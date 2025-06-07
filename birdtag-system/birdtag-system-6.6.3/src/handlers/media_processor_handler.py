import json
import os
import logging
import boto3
import tempfile
import subprocess
from typing import Dict, Any, Optional
from botocore.exceptions import ClientError

from utils.error_utils import BirdTagError, ErrorCode, create_error_response as create_error
from utils.error_utils import validate_required_fields

# Configure logging
logger = logging.getLogger()
logger.setLevel(logging.INFO)

# Initialize AWS clients
s3_client = boto3.client('s3')

# Environment variables
MEDIA_BUCKET = os.environ.get('MEDIA_BUCKET')
VIDEO_PREVIEW_PREFIX = os.environ.get('VIDEO_PREVIEW_PREFIX', 'videos/preview/')
AUDIO_WAVEFORM_PREFIX = os.environ.get('AUDIO_WAVEFORM_PREFIX', 'audio/waveform/')
FFMPEG_PATH = os.environ.get('FFMPEG_PATH', '/opt/ffmpeg/ffmpeg')

def get_cors_headers() -> Dict[str, str]:
    """Return CORS headers for HTTP responses."""
    return {
        'Content-Type': 'application/json',
        'Access-Control-Allow-Origin': '*',
        'Access-Control-Allow-Headers': 'Content-Type,X-Amz-Date,Authorization,X-Api-Key,X-Amz-Security-Token',
        'Access-Control-Allow-Methods': 'GET,POST,PUT,DELETE,OPTIONS'
    }

def process_video(video_path: str, output_path: str, timestamp: int = 5) -> None:
    """
    Extract a frame from video at specified timestamp.
    
    Args:
        video_path (str): Path to input video file
        output_path (str): Path to save the extracted frame
        timestamp (int): Timestamp in seconds to extract frame
        
    Raises:
        BirdTagError: If frame extraction fails
    """
    try:
        # Use FFmpeg to extract frame at specified timestamp
        cmd = [
            FFMPEG_PATH,
            '-i', video_path,
            '-ss', str(timestamp),
            '-vframes', '1',
            '-q:v', '2',
            output_path
        ]
        
        result = subprocess.run(cmd, capture_output=True, text=True)
        if result.returncode != 0:
            raise BirdTagError(
                message="Failed to extract video frame",
                error_code=ErrorCode.PROCESSING_ERROR,
                status_code=500,
                details={"ffmpeg_error": result.stderr}
            )
            
    except Exception as e:
        logger.error(f"Error processing video: {str(e)}")
        raise BirdTagError(
            message="Failed to process video",
            error_code=ErrorCode.PROCESSING_ERROR,
            status_code=500,
            details={"original_error": str(e)}
        )

def process_audio(audio_path: str, output_path: str) -> None:
    """
    Generate waveform visualization for audio file.
    
    Args:
        audio_path (str): Path to input audio file
        output_path (str): Path to save the waveform image
        
    Raises:
        BirdTagError: If waveform generation fails
    """
    try:
        # Use FFmpeg to generate waveform visualization
        cmd = [
            FFMPEG_PATH,
            '-i', audio_path,
            '-filter_complex', 'showwavespic=s=1280x720:colors=#3A50B1',
            '-frames:v', '1',
            output_path
        ]
        
        result = subprocess.run(cmd, capture_output=True, text=True)
        if result.returncode != 0:
            raise BirdTagError(
                message="Failed to generate audio waveform",
                error_code=ErrorCode.PROCESSING_ERROR,
                status_code=500,
                details={"ffmpeg_error": result.stderr}
            )
            
    except Exception as e:
        logger.error(f"Error processing audio: {str(e)}")
        raise BirdTagError(
            message="Failed to process audio",
            error_code=ErrorCode.PROCESSING_ERROR,
            status_code=500,
            details={"original_error": str(e)}
        )

def lambda_handler(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    """
    Handle media processing requests.
    
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
        if not MEDIA_BUCKET:
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
        
        # Determine media type and processing method
        file_extension = os.path.splitext(key)[1].lower()
        
        with tempfile.TemporaryDirectory() as temp_dir:
            # Download file from S3
            local_path = os.path.join(temp_dir, os.path.basename(key))
            s3_client.download_file(bucket, key, local_path)
            
            if file_extension in ['.mp4', '.avi', '.mov']:
                # Process video
                output_filename = f"{os.path.splitext(os.path.basename(key))[0]}_preview.jpg"
                output_path = os.path.join(temp_dir, output_filename)
                process_video(local_path, output_path)
                
                # Upload preview to S3
                s3_key = f"{VIDEO_PREVIEW_PREFIX}{output_filename}"
                s3_client.upload_file(output_path, bucket, s3_key)
                
                preview_url = s3_client.generate_presigned_url(
                    'get_object',
                    Params={'Bucket': bucket, 'Key': s3_key},
                    ExpiresIn=3600
                )
                
                return {
                    'statusCode': 200,
                    'headers': get_cors_headers(),
                    'body': json.dumps({
                        'message': 'Video preview generated successfully',
                        'preview_url': preview_url,
                        'preview_key': s3_key
                    })
                }
                
            elif file_extension in ['.wav', '.mp3', '.m4a']:
                # Process audio
                output_filename = f"{os.path.splitext(os.path.basename(key))[0]}_waveform.jpg"
                output_path = os.path.join(temp_dir, output_filename)
                process_audio(local_path, output_path)
                
                # Upload waveform to S3
                s3_key = f"{AUDIO_WAVEFORM_PREFIX}{output_filename}"
                s3_client.upload_file(output_path, bucket, s3_key)
                
                waveform_url = s3_client.generate_presigned_url(
                    'get_object',
                    Params={'Bucket': bucket, 'Key': s3_key},
                    ExpiresIn=3600
                )
                
                return {
                    'statusCode': 200,
                    'headers': get_cors_headers(),
                    'body': json.dumps({
                        'message': 'Audio waveform generated successfully',
                        'waveform_url': waveform_url,
                        'waveform_key': s3_key
                    })
                }
            else:
                raise BirdTagError(
                    message="Unsupported media type",
                    error_code=ErrorCode.INVALID_INPUT,
                    status_code=400,
                    details={"file_extension": file_extension}
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