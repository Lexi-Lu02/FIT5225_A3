import json
import os
import tempfile
import boto3
import uuid
from datetime import datetime
import logging
import traceback
import decimal
from ultralytics import YOLO
import cv2
import numpy as np
from PIL import Image
import io
import sys
from aws_lambda_powertools import Logger
from aws_lambda_powertools.utilities.typing import LambdaContext
from aws_lambda_powertools.utilities.data_classes import S3Event

# Configure environment variables for matplotlib and YOLO
os.environ['MPLCONFIGDIR'] = '/tmp/matplotlib'
os.environ['YOLO_CONFIG_DIR'] = '/tmp/ultralytics'

# Ensure required directories exist for temporary storage
os.makedirs('/tmp/matplotlib', exist_ok=True)
os.makedirs('/tmp/ultralytics', exist_ok=True)

# Initialize AWS Lambda Powertools logger for structured logging
logger = Logger()

# Initialize AWS service clients
s3 = boto3.client('s3')
try:
    ddb_table_name = os.environ['DDB_TABLE']
    logger.info(f"[INIT] DDB_TABLE environment variable: {ddb_table_name}")
    dynamodb = boto3.resource('dynamodb')
    table = dynamodb.Table(ddb_table_name)
except Exception as e:
    logger.error(f"[INIT] Error initializing DynamoDB table: {e}")
    table = None
    sys.stdout.flush()

# Global variable for model instance caching
model = None

def get_model():
    """
    Retrieve or initialize the YOLO model instance.
    Implements caching to avoid reloading the model on each invocation.
    Handles both local testing and Lambda deployment environments.
    
    Returns:
        YOLO: Initialized YOLO model instance
    """
    global model
    if model is None:
        try:
            # Check if running in local test mode
            is_local_test = os.environ.get("LOCAL_TEST") == "1"
            
            if is_local_test:
                # Local test mode: Use model file from current directory
                model_path = os.path.join(os.getcwd(), "model.pt")
                logger.info(f"Local test: Loading model from current directory: {model_path}")
            else:
                # Lambda environment: Use model file from container
                root = os.environ.get('LAMBDA_TASK_ROOT', '/var/task')
                model_path = os.environ.get('MODEL_PATH', 'model/model.pt')
                model_path = os.path.join(root, model_path)
                logger.info(f"Lambda environment: Loading model from: {model_path}")
            
            model = YOLO(model_path)
            logger.info("Model loaded successfully")
        except Exception as e:
            logger.error(f"Error loading model: {str(e)}")
            logger.error(traceback.format_exc())
            raise
    return model

def float_to_decimal(obj):
    """
    Convert float values to Decimal type for DynamoDB compatibility.
    Recursively processes nested structures (lists and dictionaries).
    
    Args:
        obj: Input object (float, list, or dict)
        
    Returns:
        Decimal or original object type
    """
    if isinstance(obj, float):
        return decimal.Decimal(str(obj))
    elif isinstance(obj, list):
        return [float_to_decimal(i) for i in obj]
    elif isinstance(obj, dict):
        return {k: float_to_decimal(v) for k, v in obj.items()}
    else:
        return obj

def move_file_to_species_folder(bucket: str, source_key: str, species_name: str) -> str:
    """
    Relocate processed image to species-specific directory in S3.
    Implements atomic move operation using copy and delete.
    
    Args:
        bucket (str): S3 bucket name
        source_key (str): Original S3 object key
        species_name (str): Detected species name for folder organization
        
    Returns:
        str: New S3 object key in species-specific directory
    """
    filename = os.path.basename(source_key)
    new_key = f"species/{species_name}/{filename}"
    # Execute S3 operations
    s3.copy_object(
        Bucket=bucket,
        CopySource={'Bucket': bucket, 'Key': source_key},
        Key=new_key
    )
    logger.info(f"[S3] Copied file to: {new_key}")
    sys.stdout.flush()
    s3.delete_object(
        Bucket=bucket,
        Key=source_key
    )
    logger.info(f"[S3] Deleted original file: {source_key}")
    sys.stdout.flush()
    return new_key

def save_to_dynamodb(
    bucket: str,
    original_key: str,
    new_key: str,
    thumbnail_key: str,
    detection_boxes: list,
    detected_species: list,
    created_at: str,
    user_id: str = None
) -> str:
    """
    Persist analysis results to DynamoDB with metadata.
    Implements error handling and logging for database operations.
    
    Args:
        bucket (str): S3 bucket name
        original_key (str): Original S3 object key
        new_key (str): New S3 object key in species folder
        thumbnail_key (str): S3 key for thumbnail image
        detection_boxes (list): List of detected bird bounding boxes
        detected_species (list): List of detected bird species
        created_at (str): ISO format timestamp
        user_id (str, optional): User identifier
        
    Returns:
        str: Generated media ID or None if operation fails
    """
    media_id = str(uuid.uuid4())
    item = {
        'id': media_id,
        'user_id': user_id,
        'file_type': 'image',
        's3_path': new_key,
        'thumbnail_path': thumbnail_key,
        'detected_species': detected_species,
        'detection_boxes': detection_boxes,
        'created_at': created_at
    }
    item = float_to_decimal(item)
    try:
        table.put_item(Item=item)
        logger.info(f"[DB] Saved analysis results to DynamoDB with ID: {media_id}")
        sys.stdout.flush()
    except Exception as e:
        logger.error(f"[DB] DynamoDB put_item failed: {e}")
        logger.error(traceback.format_exc())
        sys.stdout.flush()
        return None
    return media_id

@logger.inject_lambda_context
def lambda_handler(event: dict, context: LambdaContext) -> dict:
    """
    AWS Lambda handler for bird detection pipeline.
    Processes S3 events, coordinates image analysis, and manages data persistence.
    
    Args:
        event (dict): S3 event trigger containing file metadata
        context (LambdaContext): AWS Lambda context object
        
    Returns:
        dict: Response containing analysis results and metadata
    """
    try:
        # Parse S3 event payload with fallback for different event formats
        try:
            s3_event = S3Event(event)
            records = list(s3_event.records)
            record = records[0]
            bucket = record.s3.bucket.name
            key = record.s3.get_object.key
        except Exception:
            # Handle legacy event format
            record = event['Records'][0]
            bucket = record['s3']['bucket']['name']
            key = record['s3']['object']['key']
        
        logger.info("Processing image", extra={
            "bucket": bucket,
            "key": key,
            "is_local_test": os.environ.get("LOCAL_TEST") == "1"
        })
        
        return process_image(bucket, key)
        
    except Exception as e:
        logger.exception("Error in lambda_handler", extra={
            "error": str(e),
            "traceback": traceback.format_exc()
        })
        return {
            'statusCode': 500,
            'body': json.dumps({
                'message': 'Internal server error',
                'error': str(e)
            })
        }

def process_image(bucket: str, key: str) -> dict:
    """
    Process image through bird detection pipeline.
    Implements image download, thumbnail generation, model inference,
    and result persistence.
    
    Args:
        bucket (str): S3 bucket name
        key (str): S3 object key
        
    Returns:
        dict: Processing results including detections and metadata
    """
    try:
        # Download image to temporary storage
        local_file = f"/tmp/{os.path.basename(key)}"
        is_local_test = os.environ.get("LOCAL_TEST") == "1" or bucket == "test-bucket"
        
        logger.info("Starting image processing", extra={
            "local_file": local_file,
            "is_local_test": is_local_test
        })
        
        if is_local_test:
            import shutil
            shutil.copyfile(os.path.basename(key), local_file)
            logger.info("Local test file copied", extra={"source": os.path.basename(key), "destination": local_file})
        else:
            s3.download_file(bucket, key, local_file)
            logger.info("File downloaded from S3", extra={"bucket": bucket, "key": key, "local_path": local_file})
        
        # Generate and upload thumbnail
        thumbnail_key = f"thumbnail/{os.path.basename(key)}"
        with Image.open(local_file) as img:
            # Calculate thumbnail dimensions
            max_size = 200
            ratio = min(max_size/img.width, max_size/img.height)
            new_size = (int(img.width * ratio), int(img.height * ratio))
            # Generate thumbnail
            thumbnail = img.resize(new_size, Image.Resampling.LANCZOS)
            # Save thumbnail to memory buffer
            thumbnail_buffer = io.BytesIO()
            thumbnail.save(thumbnail_buffer, format='JPEG', quality=75)
            thumbnail_buffer.seek(0)
            # Upload thumbnail to S3
            s3.upload_fileobj(
                thumbnail_buffer,
                bucket,
                thumbnail_key,
                ExtraArgs={'ContentType': 'image/jpeg'}
            )
            logger.info("Thumbnail uploaded", extra={
                "bucket": bucket,
                "thumbnail_key": thumbnail_key,
                "original_size": (img.width, img.height),
                "thumbnail_size": new_size
            })
        
        # Execute model inference
        logger.info("Starting model inference", extra={"is_local_test": is_local_test})
        model = get_model()
        results = model(local_file)
        
        # Process detection results
        detection_boxes = []
        detected_species_set = set()
        
        for result in results:
            boxes = result.boxes
            for box in boxes:
                # Extract coordinates and confidence
                x1, y1, x2, y2 = box.xyxy[0].tolist()
                confidence = float(box.conf[0])
                class_id = int(box.cls[0])
                class_name = result.names[class_id]
                
                # Normalize coordinates
                img_height, img_width = result.orig_shape
                x1, x2 = x1/img_width, x2/img_width
                y1, y2 = y1/img_height, y2/img_height
                
                detection_boxes.append({
                    'species': class_name,
                    'code': class_name.lower().replace(' ', '_'),
                    'box': [x1, y1, x2, y2],
                    'confidence': confidence
                })
                detected_species_set.add(class_name)
        
        detected_species = list(detected_species_set)
        logger.info("Model inference completed", extra={
            "detected_species_count": len(detected_species),
            "detected_species": detected_species,
            "detection_boxes_count": len(detection_boxes)
        })
        
        # Determine primary species based on highest confidence detection
        highest_confidence_species = None
        if detection_boxes:
            highest_confidence_box = max(detection_boxes, key=lambda x: x['confidence'])
            highest_confidence_species = highest_confidence_box['species']
        else:
            highest_confidence_species = 'unknown'
        
        # Organize file in species-specific directory
        new_key = move_file_to_species_folder(bucket, key, highest_confidence_species)
        logger.info("File moved to species folder", extra={
            "original_key": key,
            "new_key": new_key,
            "species": highest_confidence_species
        })
        
        # Persist results to DynamoDB
        created_at = datetime.utcnow().isoformat()
        media_id = save_to_dynamodb(
            bucket=bucket,
            original_key=key,
            new_key=new_key,
            thumbnail_key=thumbnail_key,
            detection_boxes=detection_boxes,
            detected_species=detected_species,
            created_at=created_at
        )
        logger.info("Analysis results saved to DynamoDB", extra={"media_id": media_id})
        
        # Cleanup temporary files
        os.remove(local_file)
        logger.info("Temporary file cleaned up", extra={"file": local_file})
        
        return {
            'statusCode': 200,
            'body': json.dumps({
                'message': 'Image processed successfully',
                'record_id': media_id,
                'detected_species': detected_species,
                'detection_boxes': detection_boxes,
                'file_location': {
                    'original': key,
                    'new': new_key,
                    'thumbnail': thumbnail_key,
                    'species': highest_confidence_species
                },
                'created_at': created_at
            })
        }
        
    except Exception as e:
        logger.exception("Error processing image", extra={
            "error": str(e),
            "traceback": traceback.format_exc(),
            "bucket": bucket,
            "key": key
        })
        return {
            'statusCode': 500,
            'body': json.dumps({
                'message': 'Error processing image',
                'error': str(e)
            })
        } 
