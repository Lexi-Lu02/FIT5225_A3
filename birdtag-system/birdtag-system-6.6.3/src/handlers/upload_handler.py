import json
import os
import uuid
import logging
import base64
from urllib.parse import unquote_plus
from typing import Dict, Any, Tuple

from utils.s3_utils import (
    validate_file_extension,
    get_content_type,
    upload_file_to_s3
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

def create_success_response(file_key: str, file_id: str) -> Dict[str, Any]:
    """
    Create a successful response with proper format
    
    Args:
        file_key (str): The S3 file key
        file_id (str): The unique file ID
    
    Returns:
        dict: Lambda response
    """
    return {
        'statusCode': 200,
        'headers': get_cors_headers(),
        'body': json.dumps({
            'fileKey': file_key,
            'fileId': file_id,
            'message': 'File uploaded successfully'
        })
    }

def parse_multipart_form_data(event: Dict[str, Any]) -> Tuple[bytes, str]:
    """
    Parse multipart form data from the event
    
    Args:
        event (dict): API Gateway event
    
    Returns:
        tuple: (file_data, filename)
    """
    logger.info("Starting to parse multipart form data")
    logger.info(f"Event keys: {list(event.keys())}")
    
    if 'body' not in event:
        logger.error("No body found in event")
        raise BirdTagError(
            message="No file data provided",
            error_code=ErrorCode.INVALID_REQUEST,
            status_code=400
        )
    
    # Get content type
    content_type = event.get('headers', {}).get('Content-Type', '')
    logger.info(f"Content-Type: {content_type}")
    
    if 'multipart/form-data' not in content_type:
        logger.error(f"Invalid Content-Type: {content_type}")
        raise BirdTagError(
            message="Content-Type must be multipart/form-data",
            error_code=ErrorCode.INVALID_REQUEST,
            status_code=400
        )
    
    # Get raw body data
    body = event['body']
    logger.info(f"Body type: {type(body)}")
    
    # Decode base64 body
    try:
        logger.info("Decoding base64 body")
        body = base64.b64decode(body)
        logger.info("Successfully decoded base64 body")
    except Exception as e:
        logger.error(f"Failed to decode base64 body: {str(e)}")
        raise BirdTagError(
            message="Invalid request body format",
            error_code=ErrorCode.INVALID_REQUEST,
            status_code=400
        )
    
    # Get filename from query parameters
    query_params = event.get('queryStringParameters', {})
    logger.info(f"Query parameters: {query_params}")
    
    filename = query_params.get('filename')
    if not filename:
        logger.error("No filename provided in query parameters")
        raise BirdTagError(
            message="Filename is required",
            error_code=ErrorCode.INVALID_REQUEST,
            status_code=400
        )
    
    # Extract file data from multipart form data
    try:
        # Find the boundary
        boundary = None
        for part in content_type.split(';'):
            if 'boundary=' in part:
                boundary = part.split('=')[1].strip()
                break
        
        if not boundary:
            raise BirdTagError(
                message="No boundary found in Content-Type",
                error_code=ErrorCode.INVALID_REQUEST,
                status_code=400
            )
        
        # Split the body by boundary
        boundary_bytes = f'--{boundary}'.encode()
        parts = body.split(boundary_bytes)
        
        # Find the file part
        for part in parts:
            if not part.strip():
                continue
            
            # Look for filename in headers
            headers_end = part.find(b'\r\n\r\n')
            if headers_end == -1:
                continue
            
            headers = part[:headers_end].decode('utf-8', errors='ignore')
            if 'filename=' not in headers:
                continue
            
            # Extract file data
            data_start = headers_end + 4
            data_end = part.rfind(b'\r\n')
            if data_end == -1:
                data_end = len(part)
            
            file_data = part[data_start:data_end]
            logger.info(f"Successfully extracted file data, size: {len(file_data)} bytes")
            
            return file_data, filename
        
        raise BirdTagError(
            message="No file found in request",
            error_code=ErrorCode.INVALID_REQUEST,
            status_code=400
        )
        
    except Exception as e:
        logger.error(f"Error parsing multipart form data: {str(e)}")
        raise BirdTagError(
            message="Failed to parse file data",
            error_code=ErrorCode.INVALID_REQUEST,
            status_code=400
        )

def lambda_handler(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    """
    Lambda handler for file uploads
    
    Args:
        event (dict): API Gateway event containing file data
        context (object): Lambda context object
    
    Returns:
        dict: HTTP response with upload result or error
    """
    logger.info("Starting upload handler")
    logger.info(f"Event: {json.dumps(event)}")
    
    try:
        # Get environment variables
        bucket_name = os.environ.get('MEDIA_BUCKET')
        upload_prefix = os.environ.get('UPLOAD_PREFIX', 'uploads/')
        
        logger.info(f"Bucket name: {bucket_name}")
        logger.info(f"Upload prefix: {upload_prefix}")
        
        if not bucket_name:
            logger.error("MEDIA_BUCKET environment variable not set")
            raise BirdTagError(
                message="Server configuration error",
                error_code=ErrorCode.UNKNOWN_ERROR,
                status_code=500
            )
        
        # Ensure upload prefix ends with /
        if not upload_prefix.endswith('/'):
            upload_prefix += '/'
        
        # Parse multipart form data
        file_data, filename = parse_multipart_form_data(event)
        logger.info(f"File data size: {len(file_data)} bytes")
        
        # Validate file extension
        if not validate_file_extension(filename, ALLOWED_EXTENSIONS):
            allowed_exts = ', '.join(sorted(ALLOWED_EXTENSIONS))
            logger.error(f"Invalid file extension: {filename}")
            raise BirdTagError(
                message=f"Invalid file type. Allowed extensions: {allowed_exts}",
                error_code=ErrorCode.INVALID_FILE_TYPE,
                status_code=400
            )
        
        # Generate unique file key and ID
        file_key, file_id = generate_file_key(filename, upload_prefix)
        logger.info(f"Generated file key: {file_key}")
        logger.info(f"Generated file ID: {file_id}")
        
        # Upload file to S3
        logger.info("Attempting to upload file to S3")
        upload_file_to_s3(
            bucket_name,
            file_key,
            file_data,
            get_content_type(filename)
        )
        logger.info("Successfully uploaded file to S3")
        
        # Return success response
        return create_success_response(file_key, file_id)
    
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