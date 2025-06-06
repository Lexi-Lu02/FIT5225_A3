import json
import os
import uuid
import logging
from urllib.parse import unquote_plus
from typing import Dict, Any, Tuple

from utils.s3_utils import (
    validate_file_extension,
    get_content_type,
    generate_presigned_url
)
from utils.error_utils import (
    BirdTagError,
    ErrorCode,
    create_error_response as create_error,
    validate_required_fields
)

# Configure logging
logger = logging.getLogger()
logger.setLevel(logging.INFO)

# Allowed file extensions
ALLOWED_EXTENSIONS = {
    # Images
    'jpg', 'jpeg', 'png', 'gif', 'bmp', 'tiff', 'webp',
    # Videos
    'mp4', 'avi', 'mov', 'wmv', 'flv', 'webm', 'mkv',
    # Audio
    'mp3', 'wav', 'flac', 'aac', 'ogg', 'm4a', 'wma'
}

def get_cors_headers() -> Dict[str, str]:
    """Return CORS headers for API responses"""
    return {
        'Access-Control-Allow-Origin': '*',
        'Access-Control-Allow-Headers': 'Content-Type,X-Amz-Date,Authorization,X-Api-Key,X-Amz-Security-Token',
        'Access-Control-Allow-Methods': 'GET,POST,PUT,DELETE,OPTIONS'
    }

def generate_file_key(original_filename: str, upload_prefix: str) -> Tuple[str, str]:
    """
    Generate a unique file key with UUID
    
    Args:
        original_filename (str): The original filename
        upload_prefix (str): The S3 prefix for uploads
    
    Returns:
        tuple: (file_key, file_id)
    """
    # Generate unique file ID
    file_id = str(uuid.uuid4())
    
    # Extract file extension
    file_extension = original_filename.split('.')[-1] if '.' in original_filename else ''
    
    # Create file key with UUID and original extension
    file_key = f"{upload_prefix}{file_id}.{file_extension}"
    
    return file_key, file_id

def create_success_response(upload_url: str, file_key: str, file_id: str, expires_in: int = 3600) -> Dict[str, Any]:
    """
    Create a successful response with proper format
    
    Args:
        upload_url (str): The presigned URL
        file_key (str): The S3 file key
        file_id (str): The unique file ID
        expires_in (int): URL expiration time
    
    Returns:
        dict: Lambda response
    """
    return {
        'statusCode': 200,
        'headers': get_cors_headers(),
        'body': json.dumps({
            'uploadUrl': upload_url,
            'fileKey': file_key,
            'fileId': file_id,
            'expiresIn': expires_in,
            'message': 'Upload URL generated successfully'
        })
    }

def lambda_handler(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    """
    Lambda handler for generating S3 presigned URLs for file uploads
    
    Args:
        event (dict): API Gateway event containing query parameters
        context (object): Lambda context object
    
    Returns:
        dict: HTTP response with presigned URL or error
    """
    logger.info(f"Received event: {json.dumps(event)}")
    
    try:
        # Get environment variables
        bucket_name = os.environ.get('MEDIA_BUCKET')
        upload_prefix = os.environ.get('UPLOAD_PREFIX', 'uploads/')
        
        if not bucket_name:
            raise BirdTagError(
                message="Server configuration error",
                error_code=ErrorCode.UNKNOWN_ERROR,
                status_code=500
            )
        
        # Ensure upload prefix ends with /
        if not upload_prefix.endswith('/'):
            upload_prefix += '/'
        
        # Extract query parameters from the event
        query_params = event.get('queryStringParameters') or {}
        
        # Validate required parameters
        validate_required_fields(query_params, ['filename'])
        
        # Get and decode filename
        filename = unquote_plus(query_params['filename'])
        
        # Validate file extension
        if not validate_file_extension(filename, ALLOWED_EXTENSIONS):
            allowed_exts = ', '.join(sorted(ALLOWED_EXTENSIONS))
            raise BirdTagError(
                message=f"Invalid file type. Allowed extensions: {allowed_exts}",
                error_code=ErrorCode.INVALID_FILE_TYPE,
                status_code=400
            )
        
        # Generate unique file key and ID
        file_key, file_id = generate_file_key(filename, upload_prefix)
        
        # Set expiration time (default 1 hour)
        expires_in = int(query_params.get('expires_in', 3600))
        if expires_in > 3600:  # Max 1 hour for security
            expires_in = 3600
        
        # Generate presigned URL
        upload_url = generate_presigned_url(
            bucket_name,
            file_key,
            filename,
            get_content_type(filename),
            expires_in
        )
        
        logger.info(f"Generated presigned URL for file: {filename}, key: {file_key}")
        
        # Return success response
        return create_success_response(upload_url, file_key, file_id, expires_in)
    
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