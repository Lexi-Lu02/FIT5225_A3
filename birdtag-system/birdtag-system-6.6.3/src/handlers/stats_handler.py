import json
import logging
from typing import Dict, Any

from utils.auth_utils import require_auth
from utils.dynamo_utils import (
    get_user_stats,
    get_system_stats,
    get_species_stats
)
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
    """Handle statistics requests"""
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
        
        if path == '/v1/stats/user':
            return handle_user_stats(user_data)
        elif path == '/v1/stats/system':
            return handle_system_stats()
        elif path.startswith('/v1/stats/species/'):
            species = path.split('/')[-1]
            return handle_species_stats(species)
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

def handle_user_stats(user_data: Dict[str, Any]) -> Dict[str, Any]:
    """Handle user statistics request"""
    try:
        # Get user statistics
        stats = get_user_stats(user_data['user_id'])
        
        return {
            'statusCode': 200,
            'headers': get_cors_headers(),
            'body': json.dumps(stats)
        }
        
    except BirdTagError as e:
        raise e
    except Exception as e:
        logger.error(f"User stats error: {str(e)}")
        raise BirdTagError(
            message="Failed to get user statistics",
            error_code=ErrorCode.UNKNOWN_ERROR,
            status_code=500,
            details={"original_error": str(e)}
        )

def handle_system_stats() -> Dict[str, Any]:
    """Handle system statistics request"""
    try:
        # Get system statistics
        stats = get_system_stats()
        
        return {
            'statusCode': 200,
            'headers': get_cors_headers(),
            'body': json.dumps(stats)
        }
        
    except BirdTagError as e:
        raise e
    except Exception as e:
        logger.error(f"System stats error: {str(e)}")
        raise BirdTagError(
            message="Failed to get system statistics",
            error_code=ErrorCode.UNKNOWN_ERROR,
            status_code=500,
            details={"original_error": str(e)}
        )

def handle_species_stats(species: str) -> Dict[str, Any]:
    """Handle species statistics request"""
    try:
        # Get species statistics
        stats = get_species_stats(species)
        
        return {
            'statusCode': 200,
            'headers': get_cors_headers(),
            'body': json.dumps(stats)
        }
        
    except BirdTagError as e:
        raise e
    except Exception as e:
        logger.error(f"Species stats error: {str(e)}")
        raise BirdTagError(
            message="Failed to get species statistics",
            error_code=ErrorCode.UNKNOWN_ERROR,
            status_code=500,
            details={"original_error": str(e)}
        ) 