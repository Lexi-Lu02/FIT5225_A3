import boto3
import os
import logging
from botocore.exceptions import ClientError, ParamValidationError
from typing import Dict, Optional, Tuple, List
from .error_utils import BirdTagError, ErrorCode

# Configure logging
logger = logging.getLogger()
logger.setLevel(logging.INFO)

# Initialize S3 client
s3_client = boto3.client('s3')

# Allowed file extensions and their content types
ALLOWED_EXTENSIONS = {
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

def handle_s3_error(error: Exception, operation: str) -> None:
    """
    Handle S3 operation errors
    
    Args:
        error (Exception): The error to handle
        operation (str): The operation that failed
    
    Raises:
        BirdTagError: With appropriate error details
    """
    if isinstance(error, ClientError):
        error_code = error.response['Error']['Code']
        error_message = error.response['Error']['Message']
        
        if error_code == 'NoSuchBucket':
            raise BirdTagError(
                message=f"Bucket not found: {error_message}",
                error_code=ErrorCode.NOT_FOUND,
                status_code=404
            )
        elif error_code == 'NoSuchKey':
            raise BirdTagError(
                message=f"Object not found: {error_message}",
                error_code=ErrorCode.NOT_FOUND,
                status_code=404
            )
        elif error_code == 'AccessDenied':
            raise BirdTagError(
                message=f"Access denied: {error_message}",
                error_code=ErrorCode.FORBIDDEN,
                status_code=403
            )
        else:
            raise BirdTagError(
                message=f"S3 {operation} failed: {error_message}",
                error_code=ErrorCode.UNKNOWN_ERROR,
                status_code=500
            )
    elif isinstance(error, ParamValidationError):
        raise BirdTagError(
            message=f"Invalid parameters for S3 {operation}: {str(error)}",
            error_code=ErrorCode.INVALID_REQUEST,
            status_code=400
        )
    else:
        raise BirdTagError(
            message=f"Unexpected error during S3 {operation}: {str(error)}",
            error_code=ErrorCode.UNKNOWN_ERROR,
            status_code=500
        )

def validate_file_extension(filename: str) -> bool:
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

def get_content_type(filename: str) -> str:
    """
    Get content type based on file extension
    
    Args:
        filename (str): The filename
    
    Returns:
        str: MIME type
    """
    extension = filename.lower().split('.')[-1] if '.' in filename else ''
    return ALLOWED_EXTENSIONS.get(extension, 'application/octet-stream')

def generate_presigned_url(
    bucket_name: str,
    file_key: str,
    original_filename: str,
    expires_in: int = 3600,
    metadata: Optional[Dict] = None
) -> str:
    """
    Generate a presigned URL for S3 upload with metadata
    
    Args:
        bucket_name (str): S3 bucket name
        file_key (str): S3 object key
        original_filename (str): Original filename for metadata
        expires_in (int): URL expiration time in seconds
        metadata (dict, optional): Additional metadata to include
    
    Returns:
        str: Presigned URL
    """
    try:
        # Set metadata for the upload
        if metadata is None:
            metadata = {}
        
        metadata.update({
            'original-filename': original_filename,
        })
        
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
    
    except Exception as e:
        handle_s3_error(e, "generate presigned URL")

def download_file(bucket_name: str, file_key: str, local_path: str) -> None:
    """
    Download a file from S3 to local path
    
    Args:
        bucket_name (str): S3 bucket name
        file_key (str): S3 object key
        local_path (str): Local path to save the file
    """
    try:
        s3_client.download_file(bucket_name, file_key, local_path)
    except Exception as e:
        handle_s3_error(e, "download file")

def upload_file(local_path: str, bucket_name: str, file_key: str, metadata: Optional[Dict] = None) -> None:
    """
    Upload a file to S3
    
    Args:
        local_path (str): Local path of the file
        bucket_name (str): S3 bucket name
        file_key (str): S3 object key
        metadata (dict, optional): Additional metadata to include
    """
    try:
        extra_args = {}
        if metadata:
            extra_args['Metadata'] = metadata
        
        s3_client.upload_file(local_path, bucket_name, file_key, ExtraArgs=extra_args)
    except Exception as e:
        handle_s3_error(e, "upload file")

def copy_object(
    source_bucket: str,
    source_key: str,
    dest_bucket: str,
    dest_key: str,
    metadata: Optional[Dict] = None
) -> None:
    """
    Copy an object within S3
    
    Args:
        source_bucket (str): Source bucket name
        source_key (str): Source object key
        dest_bucket (str): Destination bucket name
        dest_key (str): Destination object key
        metadata (dict, optional): Additional metadata to include
    """
    try:
        copy_source = {'Bucket': source_bucket, 'Key': source_key}
        extra_args = {}
        if metadata:
            extra_args['Metadata'] = metadata
            extra_args['MetadataDirective'] = 'REPLACE'
        
        s3_client.copy_object(
            CopySource=copy_source,
            Bucket=dest_bucket,
            Key=dest_key,
            ExtraArgs=extra_args
        )
    except Exception as e:
        handle_s3_error(e, "copy object")

def delete_object(bucket_name: str, file_key: str) -> None:
    """
    Delete an object from S3
    
    Args:
        bucket_name (str): S3 bucket name
        file_key (str): S3 object key
    """
    try:
        s3_client.delete_object(Bucket=bucket_name, Key=file_key)
    except Exception as e:
        handle_s3_error(e, "delete object")

def get_object_metadata(bucket_name: str, file_key: str) -> Dict:
    """
    Get object metadata from S3
    
    Args:
        bucket_name (str): S3 bucket name
        file_key (str): S3 object key
    
    Returns:
        dict: Object metadata
    """
    try:
        response = s3_client.head_object(Bucket=bucket_name, Key=file_key)
        return response.get('Metadata', {})
    except Exception as e:
        handle_s3_error(e, "get object metadata")

def generate_download_url(bucket_name: str, file_key: str, expires_in: int = 3600) -> str:
    """
    Generate a presigned URL for downloading a file
    
    Args:
        bucket_name (str): S3 bucket name
        file_key (str): S3 object key
        expires_in (int): URL expiration time in seconds
    
    Returns:
        str: Presigned URL for download
    """
    try:
        return s3_client.generate_presigned_url(
            'get_object',
            Params={
                'Bucket': bucket_name,
                'Key': file_key
            },
            ExpiresIn=expires_in
        )
    except Exception as e:
        handle_s3_error(e, "generate download URL")

def upload_file_to_s3(bucket_name: str, file_key: str, file_data: bytes, content_type: str) -> None:
    """
    Upload file data directly to S3
    
    Args:
        bucket_name (str): S3 bucket name
        file_key (str): S3 object key
        file_data (bytes): File data to upload
        content_type (str): Content type of the file
    """
    try:
        s3_client.put_object(
            Bucket=bucket_name,
            Key=file_key,
            Body=file_data,
            ContentType=content_type
        )
    except Exception as e:
        handle_s3_error(e, "upload file data") 