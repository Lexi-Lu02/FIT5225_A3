import json
import boto3
import cv2
import numpy as np
from ultralytics import YOLO
import supervision as sv
import os
import tempfile
import time
import logging

# Configure logging
logger = logging.getLogger()
logger.setLevel(logging.INFO)

# Initialize AWS clients
s3_client = boto3.client('s3')
dynamodb = boto3.resource('dynamodb')

# Environment variables
MODEL_BUCKET = os.environ.get('MODEL_BUCKET')
MODEL_KEY = os.environ.get('MODEL_KEY', 'model.pt')
MEDIA_BUCKET = os.environ.get('MEDIA_BUCKET')
DYNAMODB_TABLE = os.environ.get('DYNAMODB_TABLE')

def get_cors_headers():
    """Return CORS headers for HTTP responses."""
    return {
        'Access-Control-Allow-Origin': '*',
        'Access-Control-Allow-Headers': 'Content-Type,X-Amz-Date,Authorization,X-Api-Key,X-Amz-Security-Token',
        'Access-Control-Allow-Methods': 'GET,POST,PUT,DELETE,OPTIONS'
    }

def process_image(image_path, model_path, confidence=0.5):
    """
    Process a single image and return detection results.
    
    Args:
        image_path (str): Path to the image file
        model_path (str): Path to the YOLO model
        confidence (float): Confidence threshold for detections
        
    Returns:
        tuple: (list of detection results, annotated image)
    """
    try:
        # Load YOLO model
        model = YOLO(model_path)
        
        # Read image
        img = cv2.imread(image_path)
        if img is None:
            raise Exception("Failed to read image")
        
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
        logger.error(f"Error in process_image: {str(e)}")
        raise

def lambda_handler(event, context):
    """
    Lambda function handler for processing images.
    
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
        
        # Check if triggered by S3
        if 'Records' in event and event['Records'][0]['eventSource'] == 'aws:s3':
            bucket = event['Records'][0]['s3']['bucket']['name']
            key = event['Records'][0]['s3']['object']['key']
        else:
            # Handle API Gateway request
            body = json.loads(event.get('body', '{}'))
            bucket = body.get('bucket')
            key = body.get('key')
            
            if not bucket or not key:
                return {
                    'statusCode': 400,
                    'headers': get_cors_headers(),
                    'body': json.dumps({'error': 'Missing bucket or key parameter'})
                }
        
        # Download image to temp file
        with tempfile.NamedTemporaryFile(suffix='.jpg') as tmp_file:
            s3_client.download_file(bucket, key, tmp_file.name)
            
            # Download model file if not present
            model_path = '/tmp/model.pt'
            if not os.path.exists(model_path):
                s3_client.download_file(MODEL_BUCKET, MODEL_KEY, model_path)
            
            # Process image
            detection_results, annotated_img = process_image(tmp_file.name, model_path)
            
            # Save result image
            result_key = f"results/{os.path.basename(key)}"
            with tempfile.NamedTemporaryFile(suffix='.jpg') as result_file:
                cv2.imwrite(result_file.name, annotated_img)
                s3_client.upload_file(result_file.name, MEDIA_BUCKET, result_key)
            
            # Save results to DynamoDB
            table = dynamodb.Table(DYNAMODB_TABLE)
            table.put_item(Item={
                'fileKey': key,
                'type': 'image',
                'detectionResults': detection_results,
                'resultImageKey': result_key,
                'timestamp': int(time.time())
            })
            
            return {
                'statusCode': 200,
                'headers': get_cors_headers(),
                'body': json.dumps({
                    'message': 'Processing completed',
                    'detections': detection_results,
                    'resultImageKey': result_key
                })
            }
            
    except Exception as e:
        logger.error(f"Error in lambda_handler: {str(e)}")
        return {
            'statusCode': 500,
            'headers': get_cors_headers(),
            'body': json.dumps({'error': str(e)})
        } 