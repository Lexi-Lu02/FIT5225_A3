import json
import logging
from typing import Dict, Any, Optional, Union
import os
import boto3
from botocore.exceptions import ClientError
from datetime import datetime

from ..utils.auth_utils import authenticate_user, register_user, require_auth
from ..utils.error_utils import BirdTagError, ErrorCode, create_error_response as create_error
from ..utils.error_utils import validate_required_fields

# Configure logging
logger = logging.getLogger()
logger.setLevel(logging.INFO)

# Environment variables
API_VERSION = os.environ.get('API_VERSION', 'v1')
IS_LOCAL = os.environ.get('IS_LOCAL', 'false').lower() == 'true'

cognito = boto3.client('cognito-idp')

def get_cors_headers() -> Dict[str, str]:
    """
    Return CORS headers for HTTP responses.
    
    Returns:
        Dict[str, str]: CORS headers
    """
    return {
        'Content-Type': 'application/json',
        'Access-Control-Allow-Origin': '*',
        'Access-Control-Allow-Headers': 'Content-Type,X-Amz-Date,Authorization,X-Api-Key,X-Amz-Security-Token',
        'Access-Control-Allow-Methods': 'GET,POST,PUT,DELETE,OPTIONS'
    }

def validate_request(event: Dict[str, Any]) -> None:
    """
    Validate the incoming request.
    
    Args:
        event (Dict[str, Any]): API Gateway event
        
    Raises:
        BirdTagError: If request is invalid
    """
    if not isinstance(event, dict):
        raise BirdTagError(
            message="Invalid request format",
            error_code=ErrorCode.INVALID_REQUEST,
            status_code=400
        )
        
    if 'httpMethod' not in event:
        raise BirdTagError(
            message="Missing HTTP method",
            error_code=ErrorCode.INVALID_REQUEST,
            status_code=400
        )
        
    if 'path' not in event:
        raise BirdTagError(
            message="Missing request path",
            error_code=ErrorCode.INVALID_REQUEST,
            status_code=400
        )
        
    # Skip content type validation for OPTIONS requests
    if event['httpMethod'] != 'OPTIONS':
        headers = event.get('headers', {})
        content_type = headers.get('Content-Type', '')
        if not content_type or 'application/json' not in content_type.lower():
            raise BirdTagError(
                message="Content-Type must be application/json",
                error_code=ErrorCode.INVALID_REQUEST,
                status_code=400
            )

def lambda_handler(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    """
    Handle authentication requests.
    
    Args:
        event (Dict[str, Any]): API Gateway event
        context (Any): Lambda context
        
    Returns:
        Dict[str, Any]: API Gateway response
    """
    try:
        logger.info(f"Received event: {json.dumps(event)}")
        
        # Handle CORS preflight requests
        if event.get('httpMethod') == 'OPTIONS':
            return {
                'statusCode': 200,
                'headers': get_cors_headers(),
                'body': ''
            }
        
        # Validate request
        try:
            validate_request(event)
        except BirdTagError as e:
            return create_error(e)
        
        path = event['path']
        base_path = f'/{API_VERSION}/auth'
        
        if path == f'{base_path}/login':
            return handle_login(event, context)
        elif path == f'{base_path}/register':
            return handle_register(event, context)
        elif path == f'{base_path}/verify':
            return handle_verify(event, context)
        else:
            error = BirdTagError(
                message="Not found",
                error_code=ErrorCode.NOT_FOUND,
                status_code=404
            )
            return create_error(error)
            
    except Exception as e:
        logger.error(f"Unexpected error: {str(e)}", exc_info=True)
        error = BirdTagError(
            message="An unexpected error occurred",
            error_code=ErrorCode.UNKNOWN_ERROR,
            status_code=500,
            details={"original_error": str(e)}
        )
        return create_error(error)

def handle_login(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    """
    Handle user login request.
    
    Args:
        event (Dict[str, Any]): API Gateway event
        context (Any): Lambda context
        
    Returns:
        Dict[str, Any]: API Gateway response
        
    Raises:
        BirdTagError: If login fails
    """
    try:
        body = json.loads(event['body'])
        email = body.get('email')
        password = body.get('password')

        if not email or not password:
            return {
                'statusCode': 400,
                'headers': get_cors_headers(),
                'body': json.dumps({
                    'error': 'Email and password are required'
                })
            }

        if IS_LOCAL:
            # Local test mode - check for test credentials
            if email == 'test@example.com' and password == 'Test123!':
                return {
                    'statusCode': 200,
                    'headers': get_cors_headers(),
                    'body': json.dumps({
                        'message': 'Login successful (local mode)',
                        'tokens': {
                            'AccessToken': 'local-test-token',
                            'IdToken': 'local-test-id-token',
                            'RefreshToken': 'local-test-refresh-token'
                        }
                    })
                }
            else:
                return {
                    'statusCode': 401,
                    'headers': get_cors_headers(),
                    'body': json.dumps({
                        'error': 'Invalid email or password'
                    })
                }

        try:
            response = cognito.initiate_auth(
                ClientId=os.environ['COGNITO_CLIENT_ID'],
                AuthFlow='USER_PASSWORD_AUTH',
                AuthParameters={
                    'USERNAME': email,
                    'PASSWORD': password
                }
            )
            
            return {
                'statusCode': 200,
                'headers': get_cors_headers(),
                'body': json.dumps({
                    'message': 'Login successful',
                    'tokens': response['AuthenticationResult']
                })
            }
        except ClientError as e:
            error_code = e.response['Error']['Code']
            if error_code == 'NotAuthorizedException':
                return {
                    'statusCode': 401,
                    'headers': get_cors_headers(),
                    'body': json.dumps({
                        'error': 'Invalid email or password'
                    })
                }
            else:
                raise BirdTagError(
                    message="Login failed",
                    error_code=ErrorCode.AUTH_ERROR,
                    status_code=500,
                    details={"original_error": str(e)}
                )
    except Exception as e:
        logger.error(f"Error in login: {str(e)}", exc_info=True)
        raise BirdTagError(
            message="Login failed",
            error_code=ErrorCode.AUTH_ERROR,
            status_code=500,
            details={"original_error": str(e)}
        )

def handle_register(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    """
    Handle user registration request.
    
    Args:
        event (Dict[str, Any]): API Gateway event
        context (Any): Lambda context
        
    Returns:
        Dict[str, Any]: API Gateway response
        
    Raises:
        BirdTagError: If registration fails
    """
    try:
        body = json.loads(event['body'])
        email = body.get('email')
        password = body.get('password')
        name = body.get('name')

        if not email or not password or not name:
            return {
                'statusCode': 400,
                'headers': get_cors_headers(),
                'body': json.dumps({
                    'error': 'Email, password, and name are required'
                })
            }

        if IS_LOCAL:
            # Local test mode - simulate successful registration
            return {
                'statusCode': 200,
                'headers': get_cors_headers(),
                'body': json.dumps({
                    'message': 'Registration successful (local mode)',
                    'userSub': 'local-test-user-sub'
                })
            }

        try:
            response = cognito.sign_up(
                ClientId=os.environ['COGNITO_CLIENT_ID'],
                Username=email,
                Password=password,
                UserAttributes=[
                    {
                        'Name': 'email',
                        'Value': email
                    },
                    {
                        'Name': 'name',
                        'Value': name
                    }
                ]
            )
            
            return {
                'statusCode': 200,
                'headers': get_cors_headers(),
                'body': json.dumps({
                    'message': 'Registration successful',
                    'userSub': response['UserSub']
                })
            }
        except ClientError as e:
            error_code = e.response['Error']['Code']
            if error_code == 'UsernameExistsException':
                return {
                    'statusCode': 400,
                    'headers': get_cors_headers(),
                    'body': json.dumps({
                        'error': 'Email already exists'
                    })
                }
            else:
                raise BirdTagError(
                    message="Registration failed",
                    error_code=ErrorCode.AUTH_ERROR,
                    status_code=500,
                    details={"original_error": str(e)}
                )
    except Exception as e:
        logger.error(f"Error in registration: {str(e)}", exc_info=True)
        raise BirdTagError(
            message="Registration failed",
            error_code=ErrorCode.AUTH_ERROR,
            status_code=500,
            details={"original_error": str(e)}
        )

def handle_verify(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    """
    Handle email verification request.
    
    Args:
        event (Dict[str, Any]): API Gateway event
        context (Any): Lambda context
        
    Returns:
        Dict[str, Any]: API Gateway response
        
    Raises:
        BirdTagError: If verification fails
    """
    try:
        body = json.loads(event['body'])
        email = body.get('email')
        code = body.get('code')

        if not email or not code:
            return {
                'statusCode': 400,
                'headers': get_cors_headers(),
                'body': json.dumps({
                    'error': 'Email and verification code are required'
                })
            }

        if IS_LOCAL:
            # Local test mode - simulate successful verification
            return {
                'statusCode': 200,
                'headers': get_cors_headers(),
                'body': json.dumps({
                    'message': 'Email verification successful (local mode)'
                })
            }

        try:
            cognito.confirm_sign_up(
                ClientId=os.environ['COGNITO_CLIENT_ID'],
                Username=email,
                ConfirmationCode=code
            )
            
            return {
                'statusCode': 200,
                'headers': get_cors_headers(),
                'body': json.dumps({
                    'message': 'Email verification successful'
                })
            }
        except ClientError as e:
            error_code = e.response['Error']['Code']
            if error_code == 'CodeMismatchException':
                return {
                    'statusCode': 400,
                    'headers': get_cors_headers(),
                    'body': json.dumps({
                        'error': 'Invalid verification code'
                    })
                }
            else:
                raise BirdTagError(
                    message="Verification failed",
                    error_code=ErrorCode.AUTH_ERROR,
                    status_code=500,
                    details={"original_error": str(e)}
                )
    except Exception as e:
        logger.error(f"Error in verification: {str(e)}", exc_info=True)
        raise BirdTagError(
            message="Verification failed",
            error_code=ErrorCode.AUTH_ERROR,
            status_code=500,
            details={"original_error": str(e)}
        )

def handle_resend_code(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    try:
        body = json.loads(event['body'])
        email = body.get('email')

        if not email:
            return {
                'statusCode': 400,
                'body': json.dumps({
                    'error': 'Email is required'
                })
            }

        try:
            cognito.resend_confirmation_code(
                ClientId=os.environ['COGNITO_CLIENT_ID'],
                Username=email
            )
            
            return {
                'statusCode': 200,
                'body': json.dumps({
                    'message': 'Verification code resent successfully'
                })
            }
        except ClientError as e:
            error_code = e.response['Error']['Code']
            if error_code == 'UserNotFoundException':
                return {
                    'statusCode': 404,
                    'body': json.dumps({
                        'error': 'User not found'
                    })
                }
            else:
                raise

    except Exception as e:
        print(f"Error in resending code: {str(e)}")
        return {
            'statusCode': 500,
            'body': json.dumps({
                'error': 'Internal server error'
            })
        } 