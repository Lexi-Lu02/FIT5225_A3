import json
import logging
from typing import Dict, Any

from utils.auth_utils import require_auth
from utils.model_utils import get_model_performance, get_model_status
from utils.error_utils import BirdTagError, ErrorCode, create_error_response as create_error

# Configure logging
logger = logging.getLogger()
logger.setLevel(logging.INFO)

def get_cors_headers() -> Dict[str, str]:
    """Return CORS headers for HTTP responses."""
    return {
        'Content-Type': 'application/json',
        'Access-Control-Allow-Origin': '*',
        'Access-Control-Allow-Headers': 'Content-Type,X-Amz-Date,Authorization,X-Api-Key,X-Amz-Security-Token',
        'Access-Control-Allow-Methods': 'GET,POST,PUT,DELETE,OPTIONS'
    }

def lambda_handler(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    """Handle model monitoring requests"""
    try:
        logger.info(f"Received event: {json.dumps(event)}")
        
        # Handle CORS preflight requests
        if event['httpMethod'] == 'OPTIONS':
            return {
                'statusCode': 200,
                'headers': get_cors_headers(),
                'body': ''
            }
        
        # Verify authentication
        user_data = require_auth(event)
        
        path = event['path']
        
        if path == '/v1/models/status':
            return handle_model_status(event)
        elif path == '/v1/models/performance':
            return handle_model_performance(event)
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

def handle_model_status(event: Dict[str, Any]) -> Dict[str, Any]:
    """Handle model status request"""
    try:
        # Get query parameters
        query_params = event.get('queryStringParameters', {}) or {}
        model_name = query_params.get('model')
        
        if not model_name:
            raise BirdTagError(
                message="Model name is required",
                error_code=ErrorCode.INVALID_INPUT,
                status_code=400
            )
        
        # Get model status
        status = get_model_status(model_name)
        
        return {
            'statusCode': 200,
            'headers': get_cors_headers(),
            'body': json.dumps(status)
        }
        
    except BirdTagError as e:
        raise e
    except Exception as e:
        logger.error(f"Model status error: {str(e)}")
        raise BirdTagError(
            message="Failed to get model status",
            error_code=ErrorCode.UNKNOWN_ERROR,
            status_code=500,
            details={"original_error": str(e)}
        )

def handle_model_performance(event: Dict[str, Any]) -> Dict[str, Any]:
    """Handle model performance request"""
    try:
        # Get query parameters
        query_params = event.get('queryStringParameters', {}) or {}
        model_name = query_params.get('model')
        start_date = query_params.get('startDate')
        end_date = query_params.get('endDate')
        limit = int(query_params.get('limit', 100))
        
        if not model_name:
            raise BirdTagError(
                message="Model name is required",
                error_code=ErrorCode.INVALID_INPUT,
                status_code=400
            )
        
        # Get model performance
        performance = get_model_performance(
            model_name=model_name,
            start_date=start_date,
            end_date=end_date,
            limit=limit
        )
        
        return {
            'statusCode': 200,
            'headers': get_cors_headers(),
            'body': json.dumps(performance)
        }
        
    except BirdTagError as e:
        raise e
    except Exception as e:
        logger.error(f"Model performance error: {str(e)}")
        raise BirdTagError(
            message="Failed to get model performance",
            error_code=ErrorCode.UNKNOWN_ERROR,
            status_code=500,
            details={"original_error": str(e)}
        ) 