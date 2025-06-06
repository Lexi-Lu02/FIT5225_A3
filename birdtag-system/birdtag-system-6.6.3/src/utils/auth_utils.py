import os
import jwt
import time
import logging
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
            raise BirdTagError(
                message="User not found",
                error_code=ErrorCode.UNAUTHORIZED,
                status_code=401
            )
        
        # Verify password (in production, use proper password hashing)
        if user['password'] != password:  # This is just for demonstration
            raise BirdTagError(
                message="Invalid password",
                error_code=ErrorCode.UNAUTHORIZED,
                status_code=401
            )
        
        # Generate token
        token = generate_token(user)
        
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
            raise BirdTagError(
                message="User already exists",
                error_code=ErrorCode.CONFLICT,
                status_code=409
            )
        
        # Create user
        user_data = {
            'email': email,
            'password': password,  # In production, hash the password
            'name': name,
            'createdAt': datetime.utcnow().isoformat()
        }
        
        user = create_user(user_data)
        
        # Generate token
        token = generate_token(user)
        
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
            error_code=ErrorCode.UNAUTHORIZED,
            status_code=401,
            details={"original_error": str(e)}
        ) 