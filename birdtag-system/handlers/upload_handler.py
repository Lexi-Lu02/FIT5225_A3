import json
import boto3
import os
import uuid
import logging
import time
from urllib.parse import unquote_plus
from botocore.exceptions import ClientError

# Configure logging
logger = logging.getLogger()
logger.setLevel(logging.INFO)

# Initialize S3 client
s3_client = boto3.client('s3')

# Allowed file extensions
ALLOWED_EXTENSIONS = {
    # Images
    'jpg', 'jpeg', 'png', 'gif', 'bmp', 'tiff', 'webp',
    # Videos
    'mp4', 'avi', 'mov', 'wmv', 'flv', 'webm', 'mkv',
    # Audio
    'mp3', 'wav', 'flac', 'aac', 'ogg', 'm4a', 'wma'
}

def get_cors_headers():
    #Return CORS headers for API responses
    return {
        'Access-Control-Allow-Origin': '*',
        'Access-Control-Allow-Headers': 'Content-Type,X-Amz-Date,Authorization,X-Api-Key,X-Amz-Security-Token',
        'Access-Control-Allow-Methods': 'GET,POST,PUT,DELETE,OPTIONS'
    }

def validate_file_extension(filename):
    """
    Validate if the file has an allowed extension
    
    Args:
        filename (str): The original filename
    
    Returns:
        bool: True if valid, False otherwise
    """
    if not filename:
        return False
    
    # Extract file extension
    file_extension = filename.lower().split('.')[-1] if '.' in filename else ''
    return file_extension in ALLOWED_EXTENSIONS

def generate_file_key(original_filename, upload_prefix):
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

def create_presigned_url(bucket_name, file_key, original_filename, expires_in=3600):
    """
    Generate a presigned URL for S3 upload with metadata
    
    Args:
        bucket_name (str): S3 bucket name
        file_key (str): S3 object key
        original_filename (str): Original filename for metadata
        expires_in (int): URL expiration time in seconds
    
    Returns:
        str: Presigned URL
    """
    try:
        # Set metadata for the upload
        metadata = {
            'original-filename': original_filename,
            'upload-timestamp': str(int(time.time())),
        }
        
        # Generate presigned URL with metadata
        presigned_url = s3_client.generate_presigned_url(
            'put_object',
            Params={
                'Bucket': bucket_name,
                'Key': file_key,
                'Metadata': metadata,
                'ContentType': get_content_type(original_filename)
            },
            ExpiresIn=expires_in
        )
        
        return presigned_url
    
    except ClientError as e:
        logger.error(f"Error generating presigned URL: {str(e)}")
        raise

def get_content_type(filename):
    """
    Get content type based on file extension
    
    Args:
        filename (str): The filename
    
    Returns:
        str: MIME type
    """
    extension = filename.lower().split('.')[-1] if '.' in filename else ''
    
    content_types = {
        # Images
        'jpg': 'image/jpeg', 'jpeg': 'image/jpeg', 'png': 'image/png',
        'gif': 'image/gif', 'bmp': 'image/bmp', 'tiff': 'image/tiff',
        'webp': 'image/webp',
        
        # Videos
        'mp4': 'video/mp4', 'avi': 'video/x-msvideo', 'mov': 'video/quicktime',
        'wmv': 'video/x-ms-wmv', 'flv': 'video/x-flv', 'webm': 'video/webm',
        'mkv': 'video/x-matroska',
        
        # Audio
        'mp3': 'audio/mpeg', 'wav': 'audio/wav', 'flac': 'audio/flac',
        'aac': 'audio/aac', 'ogg': 'audio/ogg', 'm4a': 'audio/mp4',
        'wma': 'audio/x-ms-wma'
    }
    
    return content_types.get(extension, 'application/octet-stream')

def create_success_response(upload_url, file_key, file_id, expires_in=3600):
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

def create_error_response(status_code, error_message):
    """
    Create an error response with proper format
    
    Args:
        status_code (int): HTTP status code
        error_message (str): Error message
    
    Returns:
        dict: Lambda response
    """
    return {
        'statusCode': status_code,
        'headers': get_cors_headers(),
        'body': json.dumps({
            'error': error_message,
            'message': 'Failed to generate upload URL'
        })
    }

def lambda_handler(event, context):
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
            logger.error("MEDIA_BUCKET environment variable not set")
            return create_error_response(500, "Server configuration error")
        
        # Ensure upload prefix ends with /
        if not upload_prefix.endswith('/'):
            upload_prefix += '/'
        
        # Extract query parameters from the event
        query_params = event.get('queryStringParameters') or {}
        
        # Get filename from query parameters
        filename = query_params.get('filename')
        if not filename:
            return create_error_response(400, "Missing required parameter: filename")
        
        # URL decode the filename if needed
        filename = unquote_plus(filename)
        
        # Validate file extension
        if not validate_file_extension(filename):
            allowed_exts = ', '.join(sorted(ALLOWED_EXTENSIONS))
            return create_error_response(400, 
                f"Invalid file type. Allowed extensions: {allowed_exts}")
        
        # Generate unique file key and ID
        file_key, file_id = generate_file_key(filename, upload_prefix)
        
        # Set expiration time (default 1 hour)
        expires_in = int(query_params.get('expires_in', 3600))
        if expires_in > 3600:  # Max 1 hour for security
            expires_in = 3600
        
        # Generate presigned URL
        upload_url = create_presigned_url(bucket_name, file_key, filename, expires_in)
        
        logger.info(f"Generated presigned URL for file: {filename}, key: {file_key}")
        
        # Return success response
        return create_success_response(upload_url, file_key, file_id, expires_in)
    
    except ClientError as e:
        logger.error(f"AWS Client Error: {str(e)}")
        return create_error_response(500, "AWS service error")
    
    except Exception as e:
        logger.error(f"Unexpected error: {str(e)}")
        return create_error_response(500, "Internal server error") 