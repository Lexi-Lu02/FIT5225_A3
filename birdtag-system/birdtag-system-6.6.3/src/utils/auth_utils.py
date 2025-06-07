import os
import jwt
import time
import logging
import bcrypt
import boto3
from typing import Dict, Any, Optional
from datetime import datetime, timedelta
from botocore.exceptions import ClientError

from utils.error_utils import BirdTagError, ErrorCode
from utils.dynamo_utils import get_user_by_email, create_user, update_user

# Configure logging
logger = logging.getLogger()
logger.setLevel(logging.INFO)

# Environment variables
JWT_SECRET = os.environ.get('JWT_SECRET')
JWT_ALGORITHM = 'HS256'
TOKEN_EXPIRY = 24 * 60 * 60  # 24 hours in seconds

# Initialize CloudWatch client
cloudwatch = boto3.client('cloudwatch')

def log_auth_metric(metric_name: str, value: int = 1):
    """
    Log authentication metrics to CloudWatch
    
    Args:
        metric_name (str): Name of the metric
        value (int): Value to log
    """
    try:
        cloudwatch.put_metric_data(
            Namespace='BirdTag/Auth',
            MetricData=[{
                'MetricName': metric_name,
                'Value': value,
                'Unit': 'Count',
                'Timestamp': datetime.utcnow()
            }]
        )
    except Exception as e:
        logger.error(f"Failed to log metric {metric_name}: {str(e)}")

def hash_password(password: str) -> str:
    """
    Hash password using bcrypt
    
    Args:
        password (str): Plain text password
        
    Returns:
        str: Hashed password
    """
    salt = bcrypt.gensalt()
    return bcrypt.hashpw(password.encode(), salt).decode()

def verify_password(password: str, hashed: str) -> bool:
    """
    Verify password against hash
    
    Args:
        password (str): Plain text password
        hashed (str): Hashed password
        
    Returns:
        bool: True if password matches hash
    """
    return bcrypt.checkpw(password.encode(), hashed.encode())

def handle_cognito_error(error: ClientError) -> BirdTagError:
    """
    Handle Cognito-specific errors
    
    Args:
        error (ClientError): AWS Cognito error
        
    Returns:
        BirdTagError: Formatted error response
    """
    error_code = error.response['Error']['Code']
    error_message = error.response['Error']['Message']
    
    error_mapping = {
        'UserNotFoundException': (ErrorCode.UNAUTHORIZED, 401, "User not found"),
        'NotAuthorizedException': (ErrorCode.UNAUTHORIZED, 401, "Invalid credentials"),
        'UserNotConfirmedException': (ErrorCode.UNAUTHORIZED, 401, "User not confirmed"),
        'UsernameExistsException': (ErrorCode.CONFLICT, 409, "User already exists"),
        'InvalidPasswordException': (ErrorCode.INVALID_INPUT, 400, "Invalid password format"),
        'InvalidParameterException': (ErrorCode.INVALID_INPUT, 400, "Invalid parameter"),
        'TooManyRequestsException': (ErrorCode.RATE_LIMIT, 429, "Too many requests")
    }
    
    if error_code in error_mapping:
        code, status, message = error_mapping[error_code]
        return BirdTagError(
            message=message,
            error_code=code,
            status_code=status,
            details={"original_error": error_message}
        )
    
    return BirdTagError(
        message="Authentication service error",
        error_code=ErrorCode.UNKNOWN_ERROR,
        status_code=500,
        details={"original_error": error_message}
    )

def generate_token(user_data: Dict[str, Any]) -> str:
    """
    Generate JWT token for user authentication
    
    Args:
        user_data (Dict[str, Any]): User data to include in token
        
    Returns:
        str: JWT token
        
    Raises:
        BirdTagError: If JWT_SECRET is not configured
    """
    if not JWT_SECRET:
        raise BirdTagError(
            message="JWT secret not configured",
            error_code=ErrorCode.CONFIGURATION_ERROR,
            status_code=500
        )
    
    # Set token expiry
    expiry = datetime.utcnow() + timedelta(seconds=TOKEN_EXPIRY)
    
    # Create token payload
    payload = {
        'user_id': user_data['userId'],
        'email': user_data['email'],
        'exp': expiry,
        'iat': datetime.utcnow()
    }
    
    # Generate token
    token = jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGORITHM)
    return token

def verify_token(token: str) -> Dict[str, Any]:
    """
    Verify JWT token and return user data
    
    Args:
        token (str): JWT token to verify
        
    Returns:
        Dict[str, Any]: User data from token
        
    Raises:
        BirdTagError: If token is invalid or expired
    """
    if not JWT_SECRET:
        raise BirdTagError(
            message="JWT secret not configured",
            error_code=ErrorCode.CONFIGURATION_ERROR,
            status_code=500
        )
    
    try:
        # Verify token
        payload = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
        return payload
    except jwt.ExpiredSignatureError:
        raise BirdTagError(
            message="Token has expired",
            error_code=ErrorCode.UNAUTHORIZED,
            status_code=401
        )
    except jwt.InvalidTokenError as e:
        raise BirdTagError(
            message="Invalid token",
            error_code=ErrorCode.UNAUTHORIZED,
            status_code=401,
            details={"original_error": str(e)}
        )

def authenticate_user(email: str, password: str) -> Dict[str, Any]:
    """
    Authenticate user with email and password
    
    Args:
        email (str): User's email
        password (str): User's password
        
    Returns:
        Dict[str, Any]: User data and token
        
    Raises:
        BirdTagError: If authentication fails
    """
    try:
        # Get user from database
        user = get_user_by_email(email)
        
        if not user:
            log_auth_metric('FailedLogin', 1)
            raise BirdTagError(
                message="User not found",
                error_code=ErrorCode.UNAUTHORIZED,
                status_code=401
            )
        
        # Verify password
        if not verify_password(password, user['password']):
            log_auth_metric('FailedLogin', 1)
            raise BirdTagError(
                message="Invalid password",
                error_code=ErrorCode.UNAUTHORIZED,
                status_code=401
            )
        
        # Generate token
        token = generate_token(user)
        
        # Log successful login
        log_auth_metric('SuccessfulLogin', 1)
        
        return {
            'user': {
                'userId': user['userId'],
                'email': user['email'],
                'name': user.get('name'),
                'createdAt': user['createdAt']
            },
            'token': token
        }
        
    except BirdTagError as e:
        raise e
    except Exception as e:
        logger.error(f"Authentication error: {str(e)}")
        log_auth_metric('AuthError', 1)
        raise BirdTagError(
            message="Authentication failed",
            error_code=ErrorCode.UNKNOWN_ERROR,
            status_code=500,
            details={"original_error": str(e)}
        )

def register_user(email: str, password: str, name: Optional[str] = None) -> Dict[str, Any]:
    """
    Register new user
    
    Args:
        email (str): User's email
        password (str): User's password
        name (Optional[str]): User's name
        
    Returns:
        Dict[str, Any]: User data and token
        
    Raises:
        BirdTagError: If registration fails
    """
    try:
        # Check if user already exists
        existing_user = get_user_by_email(email)
        if existing_user:
            log_auth_metric('FailedRegistration', 1)
            raise BirdTagError(
                message="User already exists",
                error_code=ErrorCode.CONFLICT,
                status_code=409
            )
        
        # Hash password
        hashed_password = hash_password(password)
        
        # Create user
        user_data = {
            'email': email,
            'password': hashed_password,
            'name': name,
            'createdAt': datetime.utcnow().isoformat()
        }
        
        user = create_user(user_data)
        
        # Generate token
        token = generate_token(user)
        
        # Log successful registration
        log_auth_metric('SuccessfulRegistration', 1)
        
        return {
            'user': {
                'userId': user['userId'],
                'email': user['email'],
                'name': user.get('name'),
                'createdAt': user['createdAt']
            },
            'token': token
        }
        
    except BirdTagError as e:
        raise e
    except Exception as e:
        logger.error(f"Registration error: {str(e)}")
        log_auth_metric('RegistrationError', 1)
        raise BirdTagError(
            message="Registration failed",
            error_code=ErrorCode.UNKNOWN_ERROR,
            status_code=500,
            details={"original_error": str(e)}
        )

def require_auth(event: Dict[str, Any]) -> Dict[str, Any]:
    """
    Verify authentication from API Gateway event
    
    Args:
        event (Dict[str, Any]): API Gateway event
        
    Returns:
        Dict[str, Any]: User data from token
        
    Raises:
        BirdTagError: If authentication fails
    """
    try:
        # Get token from Authorization header
        auth_header = event.get('headers', {}).get('Authorization')
        if not auth_header:
            raise BirdTagError(
                message="No authorization header",
                error_code=ErrorCode.UNAUTHORIZED,
                status_code=401
            )
        
        # Extract token
        if not auth_header.startswith('Bearer '):
            raise BirdTagError(
                message="Invalid authorization header format",
                error_code=ErrorCode.UNAUTHORIZED,
                status_code=401
            )
        
        token = auth_header.split(' ')[1]
        
        # Verify token
        return verify_token(token)
        
    except BirdTagError as e:
        raise e
    except Exception as e:
        logger.error(f"Authentication error: {str(e)}")
        raise BirdTagError(
            message="Authentication failed",
            error_code=ErrorCode.UNKNOWN_ERROR,
            status_code=500,
            details={"original_error": str(e)}
        ) 