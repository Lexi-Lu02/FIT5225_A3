import json
import os
import tempfile
import time
import logging
import boto3
from typing import Dict, Any, List, Tuple, Optional
from botocore.exceptions import ClientError
import cv2
import numpy as np
from ultralytics import YOLO
import supervision as sv

from utils.s3_utils import (
    download_file,
    upload_file,
    get_content_type
)
from utils.dynamo_utils import (
    create_media_record,
    update_media_record,
    get_media_record
)
from utils.image_utils import (
    load_image,
    convert_to_jpg,
    normalize_image
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

# Environment variables
MODEL_BUCKET = os.environ.get('MODEL_BUCKET')
MODEL_KEY = os.environ.get('MODEL_KEY', 'model.pt')
MEDIA_BUCKET = os.environ.get('MEDIA_BUCKET')
DYNAMODB_TABLE = os.environ.get('DYNAMODB_TABLE')
CACHE_TTL = int(os.environ.get('CACHE_TTL', 3600))
MAX_RETRIES = int(os.environ.get('MAX_RETRIES', 3))
CONFIDENCE_THRESHOLD = float(os.environ.get('CONFIDENCE_THRESHOLD', 0.5))

# Initialize AWS clients
dynamodb = boto3.resource('dynamodb')
table = dynamodb.Table(DYNAMODB_TABLE)

def get_cors_headers() -> Dict[str, str]:
    """Return CORS headers for HTTP responses."""
    return {
        'Access-Control-Allow-Origin': '*',
        'Access-Control-Allow-Headers': 'Content-Type,X-Amz-Date,Authorization,X-Api-Key,X-Amz-Security-Token',
        'Access-Control-Allow-Methods': 'GET,POST,PUT,DELETE,OPTIONS'
    }

def check_cache(file_key: str) -> Optional[Dict[str, Any]]:
    """
    Check if detection results are cached in DynamoDB.
    
    Args:
        file_key (str): The S3 key of the image file
        
    Returns:
        Optional[Dict[str, Any]]: Cached results if available and not expired
    """
    try:
        record = get_media_record(DYNAMODB_TABLE, file_key)
        if record and 'detectionResults' in record:
            results = record['detectionResults']
            timestamp = results.get('timestamp', 0)
            if time.time() - timestamp < CACHE_TTL:
                return results
    except Exception as e:
        logger.warning(f"Cache check failed: {str(e)}")
    return None

def process_image(
    image_path: str,
    model_path: str,
    confidence: float = CONFIDENCE_THRESHOLD,
    max_retries: int = MAX_RETRIES
) -> Tuple[List[Dict[str, Any]], np.ndarray]:
    """
    Process a single image and return detection results with retry mechanism.
    
    Args:
        image_path (str): Path to the image file
        model_path (str): Path to the YOLO model
        confidence (float): Confidence threshold for detections
        max_retries (int): Maximum number of retry attempts
        
    Returns:
        tuple: (list of detection results, annotated image)
    """
    retry_count = 0
    last_error = None
    
    while retry_count < max_retries:
        try:
            # Load YOLO model
            model = YOLO(model_path)
            
            # Read image
            img = load_image(image_path)
            if img is None:
                raise BirdTagError(
                    message="Failed to read image",
                    error_code=ErrorCode.PROCESSING_FAILED,
                    status_code=400
                )
            
            # Run detection
            result = model(img)[0]
            detections = sv.Detections.from_ultralytics(result)
            
            # Extract detection results
            detection_results = []
            if detections.class_id is not None:
                detections = detections[(detections.confidence > confidence)]
                for cls_id, conf in zip(detections.class_id, detections.confidence):
                    detection_results.append({
                        'species': model.names[cls_id],
                        'confidence': float(conf)
                    })
            
            # Create annotated image
            annotated_img = img.copy()
            if len(detection_results) > 0:
                box_annotator = sv.BoxAnnotator()
                label_annotator = sv.LabelAnnotator()
                
                box_annotator.annotate(annotated_img, detections=detections)
                labels = [f"{r['species']} {r['confidence']*100:.2f}%" for r in detection_results]
                label_annotator.annotate(annotated_img, detections=detections, labels=labels)
            
            return detection_results, annotated_img
            
        except Exception as e:
            last_error = e
            retry_count += 1
            if retry_count < max_retries:
                logger.warning(f"Retry {retry_count}/{max_retries} after error: {str(e)}")
                time.sleep(2 ** retry_count)  # Exponential backoff
            else:
                logger.error(f"All retries failed: {str(e)}")
                raise BirdTagError(
                    message="Failed to process image after multiple attempts",
                    error_code=ErrorCode.PROCESSING_FAILED,
                    status_code=500,
                    details={"original_error": str(last_error)}
                )

def lambda_handler(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    """
    Lambda function handler for processing image files.
    
    Args:
        event (dict): AWS Lambda event
        context (object): AWS Lambda context
        
    Returns:
        dict: Response with processing results
    """
    try:
        logger.info(f"Received event: {json.dumps(event)}")
        
        # Handle CORS preflight requests
        if event.get('httpMethod') == 'OPTIONS':
            return {
                'statusCode': 200,
                'headers': get_cors_headers(),
                'body': ''
            }
        
        # Check environment variables
        if not all([MODEL_BUCKET, MEDIA_BUCKET, DYNAMODB_TABLE]):
            raise BirdTagError(
                message="Missing required environment variables",
                error_code=ErrorCode.UNKNOWN_ERROR,
                status_code=500
            )
        
        # Get bucket and key from event
        if 'Records' in event and event['Records'][0]['eventSource'] == 'aws:s3':
            bucket = event['Records'][0]['s3']['bucket']['name']
            key = event['Records'][0]['s3']['object']['key']
        else:
            # Handle API Gateway request
            body = json.loads(event.get('body', '{}'))
            validate_required_fields(body, ['bucket', 'key'])
            bucket = body['bucket']
            key = body['key']
        
        # Check cache first
        cached_results = check_cache(key)
        if cached_results:
            logger.info(f"Returning cached results for {key}")
            return {
                'statusCode': 200,
                'headers': get_cors_headers(),
                'body': json.dumps({
                    'message': 'Detection results from cache',
                    'results': cached_results
                })
            }
        
        # Download image to temp file
        with tempfile.NamedTemporaryFile(suffix='.jpg') as tmp_file:
            download_file(bucket, key, tmp_file.name)
            
            # Download model file if not present
            model_path = '/tmp/model.pt'
            if not os.path.exists(model_path):
                download_file(MODEL_BUCKET, MODEL_KEY, model_path)
            
            # Process image
            detection_results, annotated_img = process_image(tmp_file.name, model_path)
            
            # Save result image
            result_key = f"results/{os.path.basename(key)}"
            with tempfile.NamedTemporaryFile(suffix='.jpg') as result_file:
                cv2.imwrite(result_file.name, annotated_img)
                upload_file(
                    result_file.name,
                    MEDIA_BUCKET,
                    result_key,
                    get_content_type(result_key)
                )
            
            # Save results to DynamoDB
            create_media_record(
                DYNAMODB_TABLE,
                key,
                'image',
                [r['species'] for r in detection_results],
                f"s3://{MEDIA_BUCKET}/{key}",
                f"s3://{MEDIA_BUCKET}/{result_key}",
                {
                    'detectionResults': detection_results,
                    'resultImageKey': result_key,
                    'timestamp': int(time.time())
                }
            )
            
            return {
                'statusCode': 200,
                'headers': get_cors_headers(),
                'body': json.dumps({
                    'message': 'Processing completed',
                    'detections': detection_results,
                    'resultImageKey': result_key
                })
            }
            
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