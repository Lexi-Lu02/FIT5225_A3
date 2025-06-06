import json
import logging
from typing import Dict, Any, Optional

from utils.auth_utils import require_auth
from utils.dynamo_utils import (
    create_tag,
    get_tag,
    update_tag,
    delete_tag,
    list_tags,
    search_tags
)
from utils.error_utils import BirdTagError, ErrorCode, create_error_response as create_error
from utils.error_utils import validate_required_fields

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
    """Handle tag management requests"""
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
        method = event['httpMethod']
        
        if path == '/v1/tags':
            if method == 'GET':
                return handle_list_tags(event)
            elif method == 'POST':
                return handle_create_tag(event, user_data)
        elif path.startswith('/v1/tags/'):
            tag_id = path.split('/')[-1]
            if method == 'GET':
                return handle_get_tag(tag_id)
            elif method == 'PUT':
                return handle_update_tag(tag_id, event)
            elif method == 'DELETE':
                return handle_delete_tag(tag_id)
        elif path == '/v1/tags/search':
            return handle_search_tags(event)
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

def handle_create_tag(event: Dict[str, Any], user_data: Dict[str, Any]) -> Dict[str, Any]:
    """Handle tag creation request"""
    try:
        body = json.loads(event['body'])
        validate_required_fields(body, ['name'])
        
        # Add user ID to tag data
        tag_data = {
            **body,
            'userId': user_data['user_id']
        }
        
        # Create tag
        tag = create_tag(tag_data)
        
        return {
            'statusCode': 201,
            'headers': get_cors_headers(),
            'body': json.dumps(tag)
        }
        
    except BirdTagError as e:
        raise e
    except Exception as e:
        logger.error(f"Create tag error: {str(e)}")
        raise BirdTagError(
            message="Failed to create tag",
            error_code=ErrorCode.UNKNOWN_ERROR,
            status_code=500,
            details={"original_error": str(e)}
        )

def handle_get_tag(tag_id: str) -> Dict[str, Any]:
    """Handle get tag request"""
    try:
        # Get tag
        tag = get_tag(tag_id)
        
        if not tag:
            raise BirdTagError(
                message="Tag not found",
                error_code=ErrorCode.NOT_FOUND,
                status_code=404
            )
        
        return {
            'statusCode': 200,
            'headers': get_cors_headers(),
            'body': json.dumps(tag)
        }
        
    except BirdTagError as e:
        raise e
    except Exception as e:
        logger.error(f"Get tag error: {str(e)}")
        raise BirdTagError(
            message="Failed to get tag",
            error_code=ErrorCode.UNKNOWN_ERROR,
            status_code=500,
            details={"original_error": str(e)}
        )

def handle_update_tag(tag_id: str, event: Dict[str, Any]) -> Dict[str, Any]:
    """Handle tag update request"""
    try:
        body = json.loads(event['body'])
        
        # Update tag
        tag = update_tag(tag_id, body)
        
        return {
            'statusCode': 200,
            'headers': get_cors_headers(),
            'body': json.dumps(tag)
        }
        
    except BirdTagError as e:
        raise e
    except Exception as e:
        logger.error(f"Update tag error: {str(e)}")
        raise BirdTagError(
            message="Failed to update tag",
            error_code=ErrorCode.UNKNOWN_ERROR,
            status_code=500,
            details={"original_error": str(e)}
        )

def handle_delete_tag(tag_id: str) -> Dict[str, Any]:
    """Handle tag deletion request"""
    try:
        # Delete tag
        delete_tag(tag_id)
        
        return {
            'statusCode': 204,
            'headers': get_cors_headers(),
            'body': ''
        }
        
    except BirdTagError as e:
        raise e
    except Exception as e:
        logger.error(f"Delete tag error: {str(e)}")
        raise BirdTagError(
            message="Failed to delete tag",
            error_code=ErrorCode.UNKNOWN_ERROR,
            status_code=500,
            details={"original_error": str(e)}
        )

def handle_list_tags(event: Dict[str, Any]) -> Dict[str, Any]:
    """Handle list tags request"""
    try:
        # Get query parameters
        query_params = event.get('queryStringParameters', {}) or {}
        limit = int(query_params.get('limit', 100))
        last_evaluated_key = query_params.get('lastEvaluatedKey')
        
        # List tags
        result = list_tags(
            limit=limit,
            last_evaluated_key=last_evaluated_key
        )
        
        return {
            'statusCode': 200,
            'headers': get_cors_headers(),
            'body': json.dumps(result)
        }
        
    except BirdTagError as e:
        raise e
    except Exception as e:
        logger.error(f"List tags error: {str(e)}")
        raise BirdTagError(
            message="Failed to list tags",
            error_code=ErrorCode.UNKNOWN_ERROR,
            status_code=500,
            details={"original_error": str(e)}
        )

def handle_search_tags(event: Dict[str, Any]) -> Dict[str, Any]:
    """Handle search tags request"""
    try:
        # Get query parameters
        query_params = event.get('queryStringParameters', {}) or {}
        query = query_params.get('q', '')
        limit = int(query_params.get('limit', 100))
        last_evaluated_key = query_params.get('lastEvaluatedKey')
        
        if not query:
            raise BirdTagError(
                message="Search query is required",
                error_code=ErrorCode.INVALID_INPUT,
                status_code=400
            )
        
        # Search tags
        result = search_tags(
            query=query,
            limit=limit,
            last_evaluated_key=last_evaluated_key
        )
        
        return {
            'statusCode': 200,
            'headers': get_cors_headers(),
            'body': json.dumps(result)
        }
        
    except BirdTagError as e:
        raise e
    except Exception as e:
        logger.error(f"Search tags error: {str(e)}")
        raise BirdTagError(
            message="Failed to search tags",
            error_code=ErrorCode.UNKNOWN_ERROR,
            status_code=500,
            details={"original_error": str(e)}
        ) 