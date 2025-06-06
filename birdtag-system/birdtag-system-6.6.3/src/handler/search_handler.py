import json
import boto3
from boto3.dynamodb.conditions import Key, Attr
import base64
import os
from decimal import Decimal
import logging
from typing import Dict, Any, List, Set

from utils.dynamo_utils import (
    search_by_tags,
    search_by_species,
    get_media_record
)
from utils.error_utils import (
    BirdTagError,
    ErrorCode,
    create_error_response as create_error,
    validate_required_fields
)

dynamodb = boto3.resource('dynamodb')
s3_client = boto3.client('s3')

# Configure logging
logger = logging.getLogger()
logger.setLevel(logging.INFO)

# Environment variables
TABLE_NAME = os.environ.get('DYNAMODB_TABLE')
MEDIA_BUCKET = os.environ.get('MEDIA_BUCKET')

def get_cors_headers() -> Dict[str, str]:
    """Return CORS headers for HTTP responses."""
    return {
        'Content-Type': 'application/json',
        'Access-Control-Allow-Origin': '*',
        'Access-Control-Allow-Headers': 'Content-Type,X-Amz-Date,Authorization,X-Api-Key,X-Amz-Security-Token',
        'Access-Control-Allow-Methods': 'GET,POST,PUT,DELETE,OPTIONS'
    }

def lambda_handler(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    """Handle different types of search queries"""
    try:
        logger.info(f"Received event: {json.dumps(event)}")
        
        # Check environment variables
        if not all([TABLE_NAME, MEDIA_BUCKET]):
            raise BirdTagError(
                message="Missing required environment variables",
                error_code=ErrorCode.UNKNOWN_ERROR,
                status_code=500
            )
        
        path = event['path']
        
        if path == '/v1/search':
            return search_by_tags(event)
        elif path == '/v1/search-by-file':
            return search_by_file(event)
        elif path == '/v1/resolve':
            return resolve_thumbnail(event)
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

def search_by_tags(event: Dict[str, Any]) -> Dict[str, Any]:
    """Search files by bird tags"""
    try:
        body = json.loads(event['body'])
        
        # Parse search criteria
        search_criteria = {}
        for bird, count in body.items():
            if isinstance(count, int):
                search_criteria[bird] = count
            else:
                # Handle case where count might be string
                search_criteria[bird] = int(count) if count else 1
        
        # Search in DynamoDB
        results = search_by_tags(
            TABLE_NAME,
            list(search_criteria.keys()),
            limit=100  # Adjust as needed
        )
        
        # Filter results based on criteria
        matching_files = []
        for item in results['items']:
            if item.get('status') == 'completed' and 'tags' in item and item['tags']:
                if matches_criteria(item['tags'], search_criteria):
                    # Determine what URL to return based on file type
                    file_url = item.get('fileUrl', '')
                    thumbnail_url = item.get('thumbnailUrl', '')
                    
                    # For images, return thumbnail if available
                    if is_image_file(file_url) and thumbnail_url:
                        matching_files.append(thumbnail_url)
                    else:
                        # For videos and audio, return full URL
                        matching_files.append(file_url)
        
        return {
            'statusCode': 200,
            'headers': get_cors_headers(),
            'body': json.dumps({
                'results': matching_files,
                'links': matching_files  # Support both 'results' and 'links' for compatibility
            })
        }
        
    except Exception as e:
        logger.error(f"Search error: {str(e)}")
        raise BirdTagError(
            message="Failed to search by tags",
            error_code=ErrorCode.DB_ERROR,
            status_code=500,
            details={"original_error": str(e)}
        )

def matches_criteria(tags: List[str], criteria: Dict[str, int]) -> bool:
    """
    Check if tags match search criteria (AND operation)
    
    Args:
        tags (List[str]): List of tags in format "species,count"
        criteria (Dict[str, int]): Search criteria with minimum counts
    
    Returns:
        bool: True if all criteria are met
    """
    tag_dict = {}
    
    # Parse tags into dictionary
    for tag in tags:
        if ',' in tag:
            species, count = tag.split(',', 1)  # Split only on first comma
            try:
                tag_dict[species.strip()] = int(count.strip())
            except ValueError:
                continue
    
    # Check if ALL criteria are met (AND operation)
    for species, min_count in criteria.items():
        if species not in tag_dict or tag_dict[species] < min_count:
            return False
    
    return True

def search_by_file(event: Dict[str, Any]) -> Dict[str, Any]:
    """Search by uploading a file and finding similar tagged files"""
    try:
        # Check if it's base64 encoded (API Gateway does this for binary data)
        if event.get('isBase64Encoded', False):
            body = base64.b64decode(event['body'])
        else:
            body = event['body']
        
        # Parse multipart form data
        # In a real implementation, you would:
        # 1. Parse the multipart boundary
        # 2. Extract the file content
        # 3. Save temporarily and process with YOLO model
        # 4. Get the detected tags
        
        # For now, simulate detected tags
        # In production, this would call the YOLO model
        detected_tags = simulate_file_processing()
        
        # Extract just the species from detected tags
        detected_species = set()
        for tag in detected_tags:
            if ',' in tag:
                species, _ = tag.split(',', 1)
                detected_species.add(species.strip())
        
        # Search for files with ANY of these species
        results = search_by_species(
            TABLE_NAME,
            list(detected_species),
            limit=100  # Adjust as needed
        )
        
        matching_files = []
        for item in results['items']:
            if item.get('status') == 'completed' and 'tags' in item and item['tags']:
                if has_any_matching_species(item['tags'], detected_species):
                    # Return appropriate URL
                    file_url = item.get('fileUrl', '')
                    thumbnail_url = item.get('thumbnailUrl', '')
                    
                    if is_image_file(file_url) and thumbnail_url:
                        matching_files.append(thumbnail_url)
                    else:
                        matching_files.append(file_url)
        
        return {
            'statusCode': 200,
            'headers': get_cors_headers(),
            'body': json.dumps({
                'results': matching_files,
                'detectedTags': list(detected_species)  # Optional: return what was detected
            })
        }
        
    except Exception as e:
        logger.error(f"Search by file error: {str(e)}")
        raise BirdTagError(
            message="Failed to search by file",
            error_code=ErrorCode.DB_ERROR,
            status_code=500,
            details={"original_error": str(e)}
        )

def has_any_matching_species(file_tags: List[str], search_species: Set[str]) -> bool:
    """
    Check if file has any of the search species
    
    Args:
        file_tags (List[str]): List of tags in format "species,count"
        search_species (Set[str]): Set of species to search for
    
    Returns:
        bool: True if any species match
    """
    for tag in file_tags:
        if ',' in tag:
            species, _ = tag.split(',', 1)
            if species.strip() in search_species:
                return True
    return False

def resolve_thumbnail(event: Dict[str, Any]) -> Dict[str, Any]:
    """Resolve thumbnail URL to full-size image URL"""
    try:
        body = json.loads(event['body'])
        validate_required_fields(body, ['thumbnailUrl'])
        
        thumbnail_url = body['thumbnailUrl'].strip()
        
        # Extract key from thumbnail URL
        original_key = None
        
        # Method 1: If URL contains 'thumbnails/' prefix
        if 'thumbnails/' in thumbnail_url:
            # Parse the URL to get the thumbnail key
            if '.amazonaws.com/' in thumbnail_url:
                parts = thumbnail_url.split('.amazonaws.com/')
                if len(parts) > 1:
                    thumbnail_key = parts[1]
                    # Convert thumbnail key to original key by replacing prefix
                    original_key = thumbnail_key.replace('thumbnails/', 'uploads/')
        
        # Method 2: Search in database by thumbnail URL
        if not original_key:
            # Search for record with matching thumbnail URL
            results = search_by_tags(
                TABLE_NAME,
                [],  # No tag filter
                limit=1
            )
            
            for item in results['items']:
                if item.get('thumbnailUrl') == thumbnail_url:
                    original_key = item.get('fileKey')
                    break
        
        if not original_key:
            raise BirdTagError(
                message="Thumbnail URL not found",
                error_code=ErrorCode.NOT_FOUND,
                status_code=404
            )
        
        # Get full URL for original image
        original_url = f"s3://{MEDIA_BUCKET}/{original_key}"
        
        return {
            'statusCode': 200,
            'headers': get_cors_headers(),
            'body': json.dumps({
                'originalUrl': original_url
            })
        }
        
    except BirdTagError as e:
        raise e
    
    except Exception as e:
        logger.error(f"Resolve thumbnail error: {str(e)}")
        raise BirdTagError(
            message="Failed to resolve thumbnail",
            error_code=ErrorCode.DB_ERROR,
            status_code=500,
            details={"original_error": str(e)}
        )

def is_image_file(url: str) -> bool:
    """Check if URL points to an image file"""
    return any(url.lower().endswith(ext) for ext in ['.jpg', '.jpeg', '.png', '.gif', '.bmp', '.webp'])

def is_video_file(url: str) -> bool:
    """Check if URL points to a video file"""
    return any(url.lower().endswith(ext) for ext in ['.mp4', '.avi', '.mov', '.wmv', '.flv', '.webm', '.mkv'])

def is_audio_file(url: str) -> bool:
    """Check if URL points to an audio file"""
    return any(url.lower().endswith(ext) for ext in ['.mp3', '.wav', '.flac', '.aac', '.ogg', '.m4a', '.wma'])

def simulate_file_processing() -> List[str]:
    """Simulate file processing with YOLO model"""
    # This is a placeholder for actual model processing
    return [
        "Common Blackbird,2",
        "European Robin,1",
        "House Sparrow,3"
    ]

# Decimal encoder for DynamoDB responses
class DecimalEncoder(json.JSONEncoder):
    def default(self, o):
        if isinstance(o, Decimal):
            return float(o)
        return super(DecimalEncoder, self).default(o)