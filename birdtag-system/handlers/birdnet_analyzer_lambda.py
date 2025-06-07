import json
import boto3
import librosa
import numpy as np
import os
import tempfile
import time
from birdnet_analyzer import analyze_audio

# Initialize AWS clients
s3_client = boto3.client('s3')
dynamodb = boto3.resource('dynamodb')

# Environment variables
MODEL_BUCKET = os.environ.get('MODEL_BUCKET')
MEDIA_BUCKET = os.environ.get('MEDIA_BUCKET')
DYNAMODB_TABLE = os.environ.get('DYNAMODB_TABLE')

def get_cors_headers():
    """Return CORS headers for HTTP responses."""
    return {
        'Access-Control-Allow-Origin': '*',
        'Access-Control-Allow-Headers': 'Content-Type',
        'Access-Control-Allow-Methods': 'OPTIONS,POST,GET'
    }

def process_audio(audio_path, model_path, confidence=0.5):
    """
    Process audio file for bird sound detection.
    
    Args:
        audio_path (str): Path to the audio file
        model_path (str): Path to the BirdNET model
        confidence (float): Confidence threshold for detections
        
    Returns:
        dict: Analysis results including detected birds and timestamps
    """
    try:
        # Load and analyze audio
        results = analyze_audio(audio_path, model_path, confidence)
        return results
    except Exception as e:
        print(f"Error processing audio: {str(e)}")
        raise

def lambda_handler(event, context):
    """
    Lambda function handler for processing audio files.
    
    Args:
        event (dict): AWS Lambda event
        context (object): AWS Lambda context
        
    Returns:
        dict: Response with analysis results
    """
    try:
        # Handle CORS preflight requests
        if event.get('httpMethod') == 'OPTIONS':
            return {
                'statusCode': 200,
                'headers': get_cors_headers(),
                'body': ''
            }
            
        # Get audio file from S3
        if 'Records' in event:
            # S3 trigger
            bucket = event['Records'][0]['s3']['bucket']['name']
            key = event['Records'][0]['s3']['object']['key']
        else:
            # API Gateway trigger
            body = json.loads(event.get('body', '{}'))
            bucket = body.get('bucket')
            key = body.get('key')
            
        if not bucket or not key:
            return {
                'statusCode': 400,
                'headers': get_cors_headers(),
                'body': json.dumps({'error': 'Missing bucket or key'})
            }
            
        # Download model files if not present
        model_dir = '/tmp/birdnet_model'
        os.makedirs(model_dir, exist_ok=True)
        
        model_path = os.path.join(model_dir, 'model.tflite')
        labels_path = os.path.join(model_dir, 'labels.txt')
        
        if not os.path.exists(model_path):
            s3_client.download_file(MODEL_BUCKET, 'birdnet/model.tflite', model_path)
        if not os.path.exists(labels_path):
            s3_client.download_file(MODEL_BUCKET, 'birdnet/labels.txt', labels_path)
            
        # Download audio to temp file
        with tempfile.NamedTemporaryFile(suffix='.wav', delete=False) as tmp_file:
            s3_client.download_file(bucket, key, tmp_file.name)
            
            # Process audio
            results = process_audio(tmp_file.name, model_path)
            
            # Save results to DynamoDB
            table = dynamodb.Table(DYNAMODB_TABLE)
            table.put_item(Item={
                'fileKey': key,
                'type': 'audio',
                'analysisResults': results,
                'timestamp': int(time.time())
            })
            
            # Clean up temp file
            os.unlink(tmp_file.name)
            
            return {
                'statusCode': 200,
                'headers': get_cors_headers(),
                'body': json.dumps({
                    'message': 'Analysis completed',
                    'results': results
                })
            }
            
    except Exception as e:
        print(f"Error: {str(e)}")
        return {
            'statusCode': 500,
            'headers': get_cors_headers(),
            'body': json.dumps({'error': str(e)})
        } 