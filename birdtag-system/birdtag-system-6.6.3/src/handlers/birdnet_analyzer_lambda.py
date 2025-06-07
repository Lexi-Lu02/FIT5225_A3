import json
import os
import tempfile
import time
import logging
import boto3
from typing import Dict, Any, List, Optional
from botocore.exceptions import ClientError
from birdnet_analyzer import analyze_audio

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
from utils.audio_utils import (
    load_audio_file,
    convert_to_wav,
    normalize_audio,
    get_audio_duration
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
MEDIA_BUCKET = os.environ.get('MEDIA_BUCKET')
DYNAMODB_TABLE = os.environ.get('DYNAMODB_TABLE')
CACHE_TTL = int(os.environ.get('CACHE_TTL', 3600))
MAX_RETRIES = int(os.environ.get('MAX_RETRIES', 3))

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
    Check if analysis results are cached in DynamoDB.
    
    Args:
        file_key (str): The S3 key of the audio file
        
    Returns:
        Optional[Dict[str, Any]]: Cached results if available and not expired
    """
    try:
        record = get_media_record(DYNAMODB_TABLE, file_key)
        if record and 'analysisResults' in record:
            results = record['analysisResults']
            timestamp = results.get('timestamp', 0)
            if time.time() - timestamp < CACHE_TTL:
                return results
    except Exception as e:
        logger.warning(f"Cache check failed: {str(e)}")
    return None

def process_audio(
    audio_path: str,
    model_path: str,
    confidence: float = 0.5,
    max_retries: int = MAX_RETRIES
) -> Dict[str, Any]:
    """
    Process audio file for bird sound detection with retry mechanism.
    
    Args:
        audio_path (str): Path to the audio file
        model_path (str): Path to the BirdNET model
        confidence (float): Confidence threshold for detections
        max_retries (int): Maximum number of retry attempts
        
    Returns:
        dict: Analysis results including detected birds and timestamps
    """
    retry_count = 0
    last_error = None
    
    while retry_count < max_retries:
        try:
            # Convert to WAV if needed
            if not audio_path.lower().endswith('.wav'):
                wav_path = audio_path + '.wav'
                convert_to_wav(audio_path, wav_path)
                audio_path = wav_path
            
            # Load and analyze audio
            results = analyze_audio(audio_path, model_path, confidence)
            
            # Add audio duration
            duration = get_audio_duration(audio_path)
            results['duration'] = duration
            
            return results
            
        except Exception as e:
            last_error = e
            retry_count += 1
            if retry_count < max_retries:
                logger.warning(f"Retry {retry_count}/{max_retries} after error: {str(e)}")
                time.sleep(2 ** retry_count)  # Exponential backoff
            else:
                logger.error(f"All retries failed: {str(e)}")
                raise BirdTagError(
                    message="Failed to process audio after multiple attempts",
                    error_code=ErrorCode.PROCESSING_FAILED,
                    status_code=500,
                    details={"original_error": str(last_error)}
                )

def lambda_handler(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    """
    Lambda function handler for processing audio files.
    
    Args:
        event (dict): AWS Lambda event
        context (object): AWS Lambda context
        
    Returns:
        dict: Response with analysis results
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
                    'message': 'Analysis results from cache',
                    'results': cached_results
                })
            }
        
        # Download model files if not present
        model_dir = '/tmp/birdnet_model'
        os.makedirs(model_dir, exist_ok=True)
        
        model_path = os.path.join(model_dir, 'model.tflite')
        labels_path = os.path.join(model_dir, 'labels.txt')
        
        if not os.path.exists(model_path):
            download_file(MODEL_BUCKET, 'birdnet/model.tflite', model_path)
        if not os.path.exists(labels_path):
            download_file(MODEL_BUCKET, 'birdnet/labels.txt', labels_path)
        
        # Download audio to temp file
        with tempfile.NamedTemporaryFile(suffix='.wav', delete=False) as tmp_file:
            download_file(bucket, key, tmp_file.name)
            
            # Process audio
            results = process_audio(tmp_file.name, model_path)
            
            # Extract detected species
            detected_species = []
            if 'results' in results:
                for detection in results['results']:
                    if detection['confidence'] >= 0.5:  # Filter by confidence
                        detected_species.append(detection['species'])
            
            # Save results to DynamoDB
            create_media_record(
                DYNAMODB_TABLE,
                key,
                'audio',
                detected_species,
                f"s3://{MEDIA_BUCKET}/{key}",
                None,
                {
                    'analysisResults': results,
                    'timestamp': int(time.time())
                }
            )
            
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