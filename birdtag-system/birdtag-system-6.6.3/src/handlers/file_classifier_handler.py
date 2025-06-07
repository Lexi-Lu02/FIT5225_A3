import json
import os
import logging
import boto3
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
SPECIES_PREFIX = os.environ.get('SPECIES_PREFIX', 'species/')

def get_cors_headers() -> Dict[str, str]:
    """Return CORS headers for HTTP responses."""
    return {
        'Content-Type': 'application/json',
        'Access-Control-Allow-Origin': '*',
        'Access-Control-Allow-Headers': 'Content-Type,X-Amz-Date,Authorization,X-Api-Key,X-Amz-Security-Token',
        'Access-Control-Allow-Methods': 'GET,POST,PUT,DELETE,OPTIONS'
    }

def get_highest_confidence_tag(tags: list) -> Optional[str]:
    """
    Get the tag with highest confidence from the detection results.
    
    Args:
        tags (list): List of tags with confidence scores
        
    Returns:
        Optional[str]: Tag with highest confidence, or None if no tags
    """
    if not tags:
        return None
    
    # Sort tags by confidence (assuming format: "species,confidence")
    sorted_tags = sorted(
        tags,
        key=lambda x: float(x.split(',')[1]) if ',' in x else 0,
        reverse=True
    )
    
    # Return the species name from the highest confidence tag
    return sorted_tags[0].split(',')[0].strip()

def move_file_to_species_folder(
    source_key: str,
    species: str,
    bucket: str = MEDIA_BUCKET
) -> str:
    """
    Move a file to its species-specific folder.
    
    Args:
        source_key (str): Original S3 key of the file
        species (str): Species name to use as folder name
        bucket (str): S3 bucket name
        
    Returns:
        str: New S3 key of the file
        
    Raises:
        BirdTagError: If file move fails
    """
    try:
        # Create new key in species folder
        filename = os.path.basename(source_key)
        new_key = f"{SPECIES_PREFIX}{species}/{filename}"
        
        # Copy object to new location
        s3_client.copy_object(
            Bucket=bucket,
            CopySource={'Bucket': bucket, 'Key': source_key},
            Key=new_key
        )
        
        # Delete original object
        s3_client.delete_object(
            Bucket=bucket,
            Key=source_key
        )
        
        logger.info(f"Moved file from {source_key} to {new_key}")
        return new_key
        
    except ClientError as e:
        logger.error(f"Failed to move file: {str(e)}")
        raise BirdTagError(
            message="Failed to move file to species folder",
            error_code=ErrorCode.S3_ERROR,
            status_code=500,
            details={"original_error": str(e)}
        )

def lambda_handler(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    """
    Handle file classification and movement requests.
    
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
            validate_required_fields(body, ['bucket', 'key', 'tags'])
            bucket = body['bucket']
            key = body['key']
            tags = body['tags']
        
        # Get highest confidence tag
        species = get_highest_confidence_tag(tags)
        if not species:
            raise BirdTagError(
                message="No valid tags found",
                error_code=ErrorCode.INVALID_INPUT,
                status_code=400
            )
        
        # Move file to species folder
        new_key = move_file_to_species_folder(key, species, bucket)
        
        return {
            'statusCode': 200,
            'headers': get_cors_headers(),
            'body': json.dumps({
                'message': 'File moved successfully',
                'originalKey': key,
                'newKey': new_key,
                'species': species
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