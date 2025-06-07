import logging
import json
from typing import Dict, Any, Optional
from enum import Enum
import os

# Configure logging
logger = logging.getLogger()
logger.setLevel(logging.INFO)

class ErrorCode(Enum):
    """Error codes for the application"""
    # General errors
    UNKNOWN_ERROR = "UNKNOWN_ERROR"
    INVALID_REQUEST = "INVALID_REQUEST"
    UNAUTHORIZED = "UNAUTHORIZED"
    FORBIDDEN = "FORBIDDEN"
    NOT_FOUND = "NOT_FOUND"
    CONFIGURATION_ERROR = "CONFIGURATION_ERROR"
    
    # File related errors
    FILE_NOT_FOUND = "FILE_NOT_FOUND"
    INVALID_FILE_TYPE = "INVALID_FILE_TYPE"
    FILE_TOO_LARGE = "FILE_TOO_LARGE"
    FILE_UPLOAD_FAILED = "FILE_UPLOAD_FAILED"
    
    # Processing errors
    PROCESSING_FAILED = "PROCESSING_FAILED"
    MODEL_LOAD_FAILED = "MODEL_LOAD_FAILED"
    INFERENCE_FAILED = "INFERENCE_FAILED"
    
    # Database errors
    DB_ERROR = "DB_ERROR"
    RECORD_NOT_FOUND = "RECORD_NOT_FOUND"
    DUPLICATE_RECORD = "DUPLICATE_RECORD"

class BirdTagError(Exception):
    """Custom exception for BirdTag application"""
    def __init__(
        self,
        message: str,
        error_code: ErrorCode = ErrorCode.UNKNOWN_ERROR,
        status_code: int = 500,
        details: Optional[Dict[str, Any]] = None,
        request_id: Optional[str] = None
    ):
        self.message = message
        self.error_code = error_code
        self.status_code = status_code
        self.details = details or {}
        self.request_id = request_id
        super().__init__(self.message)

def create_error_response(
    error: BirdTagError,
    request_id: Optional[str] = None
) -> Dict[str, Any]:
    """
    Create standardized error response
    
    Args:
        error (BirdTagError): Error object
        request_id (str, optional): Request ID for tracking
    
    Returns:
        Dict[str, Any]: Formatted error response
    """
    error_body = {
        "error": {
            "code": error.error_code.value,
            "message": error.message,
            "details": error.details
        }
    }
    
    if request_id or error.request_id:
        error_body["requestId"] = request_id or error.request_id
    
    return {
        "statusCode": error.status_code,
        "headers": {
            "Content-Type": "application/json",
            "Access-Control-Allow-Origin": "*",
            "Access-Control-Allow-Headers": "Content-Type,X-Amz-Date,Authorization,X-Api-Key,X-Amz-Security-Token",
            "Access-Control-Allow-Methods": "GET,POST,PUT,DELETE,OPTIONS"
        },
        "body": json.dumps(error_body)
    }

def handle_error(error: Exception, request_id: Optional[str] = None) -> Dict[str, Any]:
    """
    Handle any exception and convert to standardized response
    
    Args:
        error (Exception): Exception to handle
        request_id (str, optional): Request ID for tracking
    
    Returns:
        Dict[str, Any]: Formatted error response
    """
    if isinstance(error, BirdTagError):
        return create_error_response(error, request_id)
    
    # Log unexpected errors with request ID
    logger.error(
        f"Unexpected error: {str(error)}",
        extra={"request_id": request_id},
        exc_info=True
    )
    
    # Convert to BirdTagError
    bird_tag_error = BirdTagError(
        message="An unexpected error occurred",
        error_code=ErrorCode.UNKNOWN_ERROR,
        details={"original_error": str(error)},
        request_id=request_id
    )
    
    return create_error_response(bird_tag_error)

def validate_required_fields(data: Dict[str, Any], required_fields: list) -> None:
    """
    Validate required fields in request data
    
    Args:
        data (Dict[str, Any]): Request data
        required_fields (list): List of required field names
    
    Raises:
        BirdTagError: If any required field is missing
    """
    if not isinstance(data, dict):
        raise BirdTagError(
            message="Invalid request data format",
            error_code=ErrorCode.INVALID_REQUEST,
            status_code=400
        )
    
    missing_fields = [field for field in required_fields if field not in data]
    
    if missing_fields:
        raise BirdTagError(
            message="Missing required fields",
            error_code=ErrorCode.INVALID_REQUEST,
            status_code=400,
            details={"missing_fields": missing_fields}
        )

def validate_file_type(
    file_path: str,
    allowed_extensions: list,
    max_size_mb: Optional[int] = None
) -> None:
    """
    Validate file type and size
    
    Args:
        file_path (str): Path to the file
        allowed_extensions (list): List of allowed file extensions
        max_size_mb (int, optional): Maximum file size in MB
    
    Raises:
        BirdTagError: If file type or size is invalid
    """
    # Check if file exists
    if not os.path.exists(file_path):
        raise BirdTagError(
            message="File not found",
            error_code=ErrorCode.FILE_NOT_FOUND,
            status_code=404,
            details={"file_path": file_path}
        )
    
    # Check file extension
    file_ext = os.path.splitext(file_path)[1].lower().lstrip('.')
    if file_ext not in allowed_extensions:
        raise BirdTagError(
            message="Invalid file type",
            error_code=ErrorCode.INVALID_FILE_TYPE,
            status_code=400,
            details={
                "file_path": file_path,
                "file_extension": file_ext,
                "allowed_extensions": allowed_extensions
            }
        )
    
    # Check file size if max_size_mb is provided
    if max_size_mb is not None:
        file_size_mb = os.path.getsize(file_path) / (1024 * 1024)
        if file_size_mb > max_size_mb:
            raise BirdTagError(
                message="File too large",
                error_code=ErrorCode.FILE_TOO_LARGE,
                status_code=400,
                details={
                    "file_path": file_path,
                    "file_size_mb": file_size_mb,
                    "max_size_mb": max_size_mb
                }
            ) 