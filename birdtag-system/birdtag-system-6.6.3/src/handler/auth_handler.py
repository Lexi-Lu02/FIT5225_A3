import json
import logging
from typing import Dict, Any, Optional, Union
import os

from utils.auth_utils import authenticate_user, register_user, require_auth
from utils.error_utils import BirdTagError, ErrorCode, create_error_response as create_error
from utils.error_utils import validate_required_fields

# Configure logging
logger = logging.getLogger()
logger.setLevel(logging.INFO)

# Environment variables
API_VERSION = os.environ.get('API_VERSION', 'v1')

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
            error_code=ErrorCode.INVALID_INPUT,
            status_code=400
        )
        
    if 'httpMethod' not in event:
        raise BirdTagError(
            message="Missing HTTP method",
            error_code=ErrorCode.INVALID_INPUT,
            status_code=400
        )
        
    if 'path' not in event:
        raise BirdTagError(
            message="Missing request path",
            error_code=ErrorCode.INVALID_INPUT,
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
        
        # Validate request
        validate_request(event)
        
        # Handle CORS preflight requests
        if event['httpMethod'] == 'OPTIONS':
            return {
                'statusCode': 200,
                'headers': get_cors_headers(),
                'body': ''
            }
        
        path = event['path']
        base_path = f'/{API_VERSION}/auth'
        
        if path == f'{base_path}/login':
            return handle_login(event)
        elif path == f'{base_path}/register':
            return handle_register(event)
        elif path == f'{base_path}/verify':
            return handle_verify(event)
        else:
            raise BirdTagError(
                message="Not found",
                error_code=ErrorCode.NOT_FOUND,
                status_code=404
            )
            
    except BirdTagError as e:
        logger.error(f"BirdTag Error: {str(e)}")
        return create_error(e)
    
    except Exception as e:
        logger.error(f"Unexpected error: {str(e)}", exc_info=True)
        error = BirdTagError(
            message="An unexpected error occurred",
            error_code=ErrorCode.UNKNOWN_ERROR,
            status_code=500,
            details={"original_error": str(e)}
        )
        return create_error(error)

def handle_login(event: Dict[str, Any]) -> Dict[str, Any]:
    """
    Handle user login request.
    
    Args:
        event (Dict[str, Any]): API Gateway event
        
    Returns:
        Dict[str, Any]: API Gateway response
        
    Raises:
        BirdTagError: If login fails
    """
    try:
        if 'body' not in event:
            raise BirdTagError(
                message="Missing request body",
                error_code=ErrorCode.INVALID_INPUT,
                status_code=400
            )
            
        body = json.loads(event['body'])
        validate_required_fields(body, ['email', 'password'])
        
        # Validate email format
        if not isinstance(body['email'], str) or '@' not in body['email']:
            raise BirdTagError(
                message="Invalid email format",
                error_code=ErrorCode.INVALID_INPUT,
                status_code=400
            )
            
        # Validate password
        if not isinstance(body['password'], str) or len(body['password']) < 6:
            raise BirdTagError(
                message="Password must be at least 6 characters",
                error_code=ErrorCode.INVALID_INPUT,
                status_code=400
            )
        
        # Authenticate user
        result = authenticate_user(body['email'], body['password'])
        
        return {
            'statusCode': 200,
            'headers': get_cors_headers(),
            'body': json.dumps(result)
        }
        
    except json.JSONDecodeError:
        raise BirdTagError(
            message="Invalid JSON in request body",
            error_code=ErrorCode.INVALID_INPUT,
            status_code=400
        )
    except BirdTagError as e:
        raise e
    except Exception as e:
        logger.error(f"Login error: {str(e)}")
        raise BirdTagError(
            message="Login failed",
            error_code=ErrorCode.UNKNOWN_ERROR,
            status_code=500,
            details={"original_error": str(e)}
        )

def handle_register(event: Dict[str, Any]) -> Dict[str, Any]:
    """
    Handle user registration request.
    
    Args:
        event (Dict[str, Any]): API Gateway event
        
    Returns:
        Dict[str, Any]: API Gateway response
        
    Raises:
        BirdTagError: If registration fails
    """
    try:
        if 'body' not in event:
            raise BirdTagError(
                message="Missing request body",
                error_code=ErrorCode.INVALID_INPUT,
                status_code=400
            )
            
        body = json.loads(event['body'])
        validate_required_fields(body, ['email', 'password'])
        
        # Validate email format
        if not isinstance(body['email'], str) or '@' not in body['email']:
            raise BirdTagError(
                message="Invalid email format",
                error_code=ErrorCode.INVALID_INPUT,
                status_code=400
            )
            
        # Validate password
        if not isinstance(body['password'], str) or len(body['password']) < 6:
            raise BirdTagError(
                message="Password must be at least 6 characters",
                error_code=ErrorCode.INVALID_INPUT,
                status_code=400
            )
            
        # Validate name if provided
        name = body.get('name')
        if name is not None and not isinstance(name, str):
            raise BirdTagError(
                message="Name must be a string",
                error_code=ErrorCode.INVALID_INPUT,
                status_code=400
            )
        
        # Register user
        result = register_user(
            email=body['email'],
            password=body['password'],
            name=name
        )
        
        return {
            'statusCode': 201,
            'headers': get_cors_headers(),
            'body': json.dumps(result)
        }
        
    except json.JSONDecodeError:
        raise BirdTagError(
            message="Invalid JSON in request body",
            error_code=ErrorCode.INVALID_INPUT,
            status_code=400
        )
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

def handle_verify(event: Dict[str, Any]) -> Dict[str, Any]:
    """
    Handle token verification request.
    
    Args:
        event (Dict[str, Any]): API Gateway event
        
    Returns:
        Dict[str, Any]: API Gateway response
        
    Raises:
        BirdTagError: If verification fails
    """
    try:
        # Verify token
        user_data = require_auth(event)
        
        return {
            'statusCode': 200,
            'headers': get_cors_headers(),
            'body': json.dumps({
                'user': {
                    'userId': user_data['user_id'],
                    'email': user_data['email']
                }
            })
        }
        
    except BirdTagError as e:
        raise e
    except Exception as e:
        logger.error(f"Verification error: {str(e)}")
        raise BirdTagError(
            message="Token verification failed",
            error_code=ErrorCode.UNKNOWN_ERROR,
            status_code=500,
            details={"original_error": str(e)}
        ) 