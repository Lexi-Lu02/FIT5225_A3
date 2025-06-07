import json
import os
import tempfile
import logging
from typing import Dict, Any, Tuple
import boto3
from PIL import Image
from botocore.exceptions import ClientError

# Configure logging
logger = logging.getLogger()
logger.setLevel(logging.INFO)

# Initialize AWS clients
s3_client = boto3.client('s3')

# Environment variables
MEDIA_BUCKET = os.environ.get('MEDIA_BUCKET')
THUMBNAIL_PREFIX = os.environ.get('THUMBNAIL_PREFIX', 'thumbnails/')
MAX_THUMBNAIL_SIZE = int(os.environ.get('MAX_THUMBNAIL_SIZE', 200))
THUMBNAIL_QUALITY = int(os.environ.get('THUMBNAIL_QUALITY', 75))

def get_cors_headers() -> Dict[str, str]:
    """Return CORS headers for HTTP responses."""
    return {
        'Access-Control-Allow-Origin': '*',
        'Access-Control-Allow-Headers': 'Content-Type,X-Amz-Date,Authorization,X-Api-Key,X-Amz-Security-Token',
        'Access-Control-Allow-Methods': 'GET,POST,PUT,DELETE,OPTIONS'
    }

def create_thumbnail(image_path: str) -> Tuple[str, str]:
    """
    Create a thumbnail from the given image.
    
    Args:
        image_path (str): Path to the source image
        
    Returns:
        tuple: (thumbnail path, content type)
    """
    try:
        # Open the image
        with Image.open(image_path) as img:
            # Convert to RGB if necessary
            if img.mode in ('RGBA', 'P'):
                img = img.convert('RGB')
            
            # Calculate new dimensions while maintaining aspect ratio
            width, height = img.size
            if width > height:
                new_width = min(width, MAX_THUMBNAIL_SIZE)
                new_height = int(height * (new_width / width))
            else:
                new_height = min(height, MAX_THUMBNAIL_SIZE)
                new_width = int(width * (new_height / height))
            
            # Resize image
            img = img.resize((new_width, new_height), Image.Resampling.LANCZOS)
            
            # Save thumbnail to temporary file
            with tempfile.NamedTemporaryFile(suffix='.jpg', delete=False) as tmp_file:
                img.save(tmp_file.name, 'JPEG', quality=THUMBNAIL_QUALITY)
                return tmp_file.name, 'image/jpeg'
                
    except Exception as e:
        logger.error(f"Error creating thumbnail: {str(e)}")
        raise

def lambda_handler(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    """
    Lambda function handler for generating thumbnails.
    
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
            raise ValueError("Missing required environment variables")
        
        # Get bucket and key from event
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
                    'body': json.dumps({
                        'message': 'Missing required parameters: bucket and key'
                    })
                }
        
        # Download image to temp file
        with tempfile.NamedTemporaryFile(suffix='.jpg') as tmp_file:
            s3_client.download_file(bucket, key, tmp_file.name)
            
            # Create thumbnail
            thumbnail_path, content_type = create_thumbnail(tmp_file.name)
            
            # Generate thumbnail key
            filename = os.path.basename(key)
            thumbnail_key = f"{THUMBNAIL_PREFIX}{filename}"
            
            # Upload thumbnail to S3
            with open(thumbnail_path, 'rb') as thumbnail_file:
                s3_client.upload_fileobj(
                    thumbnail_file,
                    bucket,
                    thumbnail_key,
                    ExtraArgs={
                        'ContentType': content_type,
                        'CacheControl': 'max-age=31536000'
                    }
                )
            
            # Clean up temporary files
            os.unlink(thumbnail_path)
            
            return {
                'statusCode': 200,
                'headers': get_cors_headers(),
                'body': json.dumps({
                    'message': 'Thumbnail generated successfully',
                    'thumbnail_key': thumbnail_key
                })
            }
            
    except ClientError as e:
        logger.error(f"AWS Error: {str(e)}")
        return {
            'statusCode': 500,
            'headers': get_cors_headers(),
            'body': json.dumps({
                'message': 'Error processing image',
                'error': str(e)
            })
        }
        
    except Exception as e:
        logger.error(f"Unexpected error: {str(e)}")
        return {
            'statusCode': 500,
            'headers': get_cors_headers(),
            'body': json.dumps({
                'message': 'An unexpected error occurred',
                'error': str(e)
            })
        } 