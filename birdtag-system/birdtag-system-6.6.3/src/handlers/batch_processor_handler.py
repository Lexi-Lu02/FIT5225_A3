import json
import logging
import uuid
from typing import Dict, Any, List
from concurrent.futures import ThreadPoolExecutor, as_completed

from utils.auth_utils import require_auth
from utils.s3_utils import download_file, upload_file
from utils.dynamo_utils import create_batch_job, update_batch_job, get_batch_job
from utils.model_utils import ModelMetrics, validate_model_input
from utils.error_utils import BirdTagError, ErrorCode, create_error_response as create_error
from utils.error_utils import validate_required_fields

# Configure logging
logger = logging.getLogger()
logger.setLevel(logging.INFO)

# Environment variables
MEDIA_BUCKET = os.environ.get('MEDIA_BUCKET')
MAX_CONCURRENT_TASKS = 5  # Maximum number of concurrent processing tasks

def get_cors_headers() -> Dict[str, str]:
    """Return CORS headers for HTTP responses."""
    return {
        'Content-Type': 'application/json',
        'Access-Control-Allow-Origin': '*',
        'Access-Control-Allow-Headers': 'Content-Type,X-Amz-Date,Authorization,X-Api-Key,X-Amz-Security-Token',
        'Access-Control-Allow-Methods': 'GET,POST,PUT,DELETE,OPTIONS'
    }

def lambda_handler(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    """Handle batch processing requests"""
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
        
        if path == '/v1/batch/process':
            return handle_batch_process(event, user_data)
        elif path.startswith('/v1/batch/status/'):
            job_id = path.split('/')[-1]
            return handle_batch_status(job_id)
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

def handle_batch_process(event: Dict[str, Any], user_data: Dict[str, Any]) -> Dict[str, Any]:
    """Handle batch processing request"""
    try:
        body = json.loads(event['body'])
        validate_required_fields(body, ['files', 'type'])
        
        files = body['files']
        process_type = body['type']
        
        if not files:
            raise BirdTagError(
                message="No files provided",
                error_code=ErrorCode.INVALID_INPUT,
                status_code=400
            )
        
        if process_type not in ['image', 'audio']:
            raise BirdTagError(
                message="Invalid process type. Must be 'image' or 'audio'",
                error_code=ErrorCode.INVALID_INPUT,
                status_code=400
            )
        
        # Create batch job
        job_id = str(uuid.uuid4())
        job_data = {
            'jobId': job_id,
            'userId': user_data['user_id'],
            'type': process_type,
            'status': 'processing',
            'totalFiles': len(files),
            'processedFiles': 0,
            'failedFiles': 0,
            'results': [],
            'createdAt': datetime.utcnow().isoformat()
        }
        
        create_batch_job(job_data)
        
        # Start processing in background
        process_batch_files(job_id, files, process_type, user_data)
        
        return {
            'statusCode': 202,
            'headers': get_cors_headers(),
            'body': json.dumps({
                'jobId': job_id,
                'message': 'Batch processing started'
            })
        }
        
    except BirdTagError as e:
        raise e
    except Exception as e:
        logger.error(f"Batch process error: {str(e)}")
        raise BirdTagError(
            message="Failed to start batch processing",
            error_code=ErrorCode.UNKNOWN_ERROR,
            status_code=500,
            details={"original_error": str(e)}
        )

def handle_batch_status(job_id: str) -> Dict[str, Any]:
    """Handle batch job status request"""
    try:
        # Get job status
        job = get_batch_job(job_id)
        
        if not job:
            raise BirdTagError(
                message="Job not found",
                error_code=ErrorCode.NOT_FOUND,
                status_code=404
            )
        
        return {
            'statusCode': 200,
            'headers': get_cors_headers(),
            'body': json.dumps(job)
        }
        
    except BirdTagError as e:
        raise e
    except Exception as e:
        logger.error(f"Batch status error: {str(e)}")
        raise BirdTagError(
            message="Failed to get batch job status",
            error_code=ErrorCode.UNKNOWN_ERROR,
            status_code=500,
            details={"original_error": str(e)}
        )

def process_batch_files(
    job_id: str,
    files: List[Dict[str, Any]],
    process_type: str,
    user_data: Dict[str, Any]
) -> None:
    """
    Process batch files in parallel
    
    Args:
        job_id (str): Batch job ID
        files (List[Dict[str, Any]]): List of files to process
        process_type (str): Type of processing (image/audio)
        user_data (Dict[str, Any]): User data
    """
    try:
        # Initialize metrics
        metrics = ModelMetrics(f"{process_type}_detection")
        
        # Process files in parallel
        with ThreadPoolExecutor(max_workers=MAX_CONCURRENT_TASKS) as executor:
            futures = []
            
            for file_info in files:
                future = executor.submit(
                    process_single_file,
                    file_info,
                    process_type,
                    user_data,
                    metrics
                )
                futures.append(future)
            
            # Collect results
            results = []
            failed_files = 0
            
            for future in as_completed(futures):
                try:
                    result = future.result()
                    results.append(result)
                except Exception as e:
                    logger.error(f"File processing error: {str(e)}")
                    failed_files += 1
            
            # Update job status
            update_batch_job(
                job_id,
                {
                    'status': 'completed',
                    'processedFiles': len(files) - failed_files,
                    'failedFiles': failed_files,
                    'results': results
                }
            )
            
    except Exception as e:
        logger.error(f"Batch processing error: {str(e)}")
        update_batch_job(
            job_id,
            {
                'status': 'failed',
                'error': str(e)
            }
        )

def process_single_file(
    file_info: Dict[str, Any],
    process_type: str,
    user_data: Dict[str, Any],
    metrics: ModelMetrics
) -> Dict[str, Any]:
    """
    Process a single file
    
    Args:
        file_info (Dict[str, Any]): File information
        process_type (str): Type of processing (image/audio)
        user_data (Dict[str, Any]): User data
        metrics (ModelMetrics): Metrics tracker
        
    Returns:
        Dict[str, Any]: Processing result
    """
    try:
        # Download file
        file_path = download_file(file_info['key'])
        
        # Validate file
        validate_model_input(file_path, process_type)
        
        # Process file based on type
        if process_type == 'image':
            result = process_image(file_path, metrics)
        else:
            result = process_audio(file_path, metrics)
        
        # Upload result
        result_key = f"results/{user_data['user_id']}/{uuid.uuid4()}.json"
        upload_file(result_key, json.dumps(result))
        
        return {
            'fileKey': file_info['key'],
            'resultKey': result_key,
            'success': True,
            'detections': result.get('detections', [])
        }
        
    except Exception as e:
        logger.error(f"File processing error: {str(e)}")
        metrics.set_error(str(e))
        return {
            'fileKey': file_info['key'],
            'success': False,
            'error': str(e)
        }
    finally:
        # Complete metrics
        metrics.complete()

def process_image(file_path: str, metrics: ModelMetrics) -> Dict[str, Any]:
    """
    Process image file
    
    Args:
        file_path (str): Path to image file
        metrics (ModelMetrics): Metrics tracker
        
    Returns:
        Dict[str, Any]: Processing result
    """
    # TODO: Implement image processing with YOLO model
    # This is a placeholder implementation
    return {
        'detections': [
            {
                'species': 'Common Blackbird',
                'confidence': 0.95,
                'bbox': [100, 100, 200, 200]
            }
        ]
    }

def process_audio(file_path: str, metrics: ModelMetrics) -> Dict[str, Any]:
    """
    Process audio file
    
    Args:
        file_path (str): Path to audio file
        metrics (ModelMetrics): Metrics tracker
        
    Returns:
        Dict[str, Any]: Processing result
    """
    # TODO: Implement audio processing with BirdNET-Analyzer
    # This is a placeholder implementation
    return {
        'detections': [
            {
                'species': 'European Robin',
                'confidence': 0.88,
                'time': '00:00:05'
            }
        ]
    } 