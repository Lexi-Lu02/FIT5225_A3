import json
import boto3
from boto3.dynamodb.conditions import Key, Attr
import base64
import os
from decimal import Decimal

dynamodb = boto3.resource('dynamodb')
s3_client = boto3.client('s3')

TABLE_NAME = os.environ['DYNAMODB_TABLE']
MEDIA_BUCKET = os.environ['MEDIA_BUCKET']

def lambda_handler(event, context):
    """Handle different types of search queries"""
    try:
        path = event['path']
        
        if path == '/v1/search':
            return search_by_tags(event)
        elif path == '/v1/search-by-file':
            return search_by_file(event)
        elif path == '/v1/resolve':
            return resolve_thumbnail(event)
        else:
            return {
                'statusCode': 404,
                'headers': {
                    'Content-Type': 'application/json',
                    'Access-Control-Allow-Origin': '*'
                },
                'body': json.dumps({'error': 'Not found'})
            }
            
    except Exception as e:
        print(f"Error: {str(e)}")
        return {
            'statusCode': 500,
            'headers': {
                'Content-Type': 'application/json',
                'Access-Control-Allow-Origin': '*'
            },
            'body': json.dumps({'error': str(e)})
        }

def search_by_tags(event):
    """Search files by bird tags - handles both with counts and species only"""
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
        
        # Query database
        table = dynamodb.Table(TABLE_NAME)
        
        # Scan all items (in production, consider using GSI for better performance)
        response = table.scan()
        items = response['Items']
        
        # Continue scanning if there are more items
        while 'LastEvaluatedKey' in response:
            response = table.scan(ExclusiveStartKey=response['LastEvaluatedKey'])
            items.extend(response['Items'])
        
        # Filter results based on criteria
        matching_files = []
        for item in items:
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
            'headers': {
                'Content-Type': 'application/json',
                'Access-Control-Allow-Origin': '*',
                'Access-Control-Allow-Headers': 'Content-Type,Authorization',
                'Access-Control-Allow-Methods': 'OPTIONS,POST,GET'
            },
            'body': json.dumps({
                'results': matching_files,
                'links': matching_files  # Support both 'results' and 'links' for compatibility
            })
        }
        
    except Exception as e:
        print(f"Search error: {str(e)}")
        return {
            'statusCode': 500,
            'headers': {
                'Content-Type': 'application/json',
                'Access-Control-Allow-Origin': '*'
            },
            'body': json.dumps({'error': str(e)})
        }

def matches_criteria(tags, criteria):
    """Check if tags match search criteria (AND operation)"""
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

def search_by_file(event):
    """Search by uploading a file and finding similar tagged files"""
    try:
        # Check if it's base64 encoded (API Gateway does this for binary data)
        if event.get('isBase64Encoded', False):
            body = base64.b64decode(event['body'])
        else:
            body = event['body']
        
        # This would call the YOLO model
        detected_tags = model_processing()
        
        # Extract just the species from detected tags
        detected_species = set()
        for tag in detected_tags:
            if ',' in tag:
                species, _ = tag.split(',', 1)
                detected_species.add(species.strip())
        
        # Search for files with ANY of these species
        table = dynamodb.Table(TABLE_NAME)
        response = table.scan()
        items = response['Items']
        
        while 'LastEvaluatedKey' in response:
            response = table.scan(ExclusiveStartKey=response['LastEvaluatedKey'])
            items.extend(response['Items'])
        
        matching_files = []
        for item in items:
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
            'headers': {
                'Content-Type': 'application/json',
                'Access-Control-Allow-Origin': '*',
                'Access-Control-Allow-Headers': 'Content-Type,Authorization',
                'Access-Control-Allow-Methods': 'OPTIONS,POST'
            },
            'body': json.dumps({
                'results': matching_files,
                'detectedTags': list(detected_species)  # Optional: return what was detected
            })
        }
        
    except Exception as e:
        print(f"Search by file error: {str(e)}")
        return {
            'statusCode': 500,
            'headers': {
                'Content-Type': 'application/json',
                'Access-Control-Allow-Origin': '*'
            },
            'body': json.dumps({'error': str(e)})
        }

def resolve_thumbnail(event):
    """Resolve thumbnail URL to full-size image URL"""
    try:
        body = json.loads(event['body'])
        thumbnail_url = body.get('thumbnailUrl', '').strip()
        
        if not thumbnail_url:
            return {
                'statusCode': 400,
                'headers': {
                    'Content-Type': 'application/json',
                    'Access-Control-Allow-Origin': '*'
                },
                'body': json.dumps({'error': 'Thumbnail URL is required'})
            }
        
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
            table = dynamodb.Table(TABLE_NAME)
            response = table.scan(
                FilterExpression=Attr('thumbnailUrl').eq(thumbnail_url)
            )
            
            if response['Items']:
                item = response['Items'][0]
                return {
                    'statusCode': 200,
                    'headers': {
                        'Content-Type': 'application/json',
                        'Access-Control-Allow-Origin': '*'
                    },
                    'body': json.dumps({
                        'originalUrl': item.get('fileUrl', ''),
                        'fileKey': item.get('fileKey', '')
                    })
                }
        else:
            # Query database for original file using the key
            table = dynamodb.Table(TABLE_NAME)
            response = table.get_item(Key={'fileKey': original_key})
            
            if 'Item' in response:
                return {
                    'statusCode': 200,
                    'headers': {
                        'Content-Type': 'application/json',
                        'Access-Control-Allow-Origin': '*'
                    },
                    'body': json.dumps({
                        'originalUrl': response['Item'].get('fileUrl', ''),
                        'fileKey': original_key
                    })
                }
        
        return {
            'statusCode': 404,
            'headers': {
                'Content-Type': 'application/json',
                'Access-Control-Allow-Origin': '*'
            },
            'body': json.dumps({'error': 'Original file not found'})
        }
        
    except Exception as e:
        print(f"Resolve error: {str(e)}")
        return {
            'statusCode': 500,
            'headers': {
                'Content-Type': 'application/json',
                'Access-Control-Allow-Origin': '*'
            },
            'body': json.dumps({'error': str(e)})
        }

def has_any_matching_species(file_tags, search_species):
    """Check if file has any of the species we're searching for"""
    for tag in file_tags:
        if ',' in tag:
            species, _ = tag.split(',', 1)
            if species.strip() in search_species:
                return True
    return False

def is_image_file(url):
    """Check if URL points to an image file"""
    if not url:
        return False
    lower_url = url.lower()
    return any(lower_url.endswith(ext) for ext in ['.jpg', '.jpeg', '.png', '.gif', '.webp'])

def is_video_file(url):
    """Check if URL points to a video file"""
    if not url:
        return False
    lower_url = url.lower()
    return any(lower_url.endswith(ext) for ext in ['.mp4', '.avi', '.mov', '.mkv', '.webm'])

def is_audio_file(url):
    """Check if URL points to an audio file"""
    if not url:
        return False
    lower_url = url.lower()
    return any(lower_url.endswith(ext) for ext in ['.mp3', '.wav', '.m4a', '.flac'])

def model_processing():
    """actual YOLO model processing"""
    # 1. Save the uploaded file temporarily
    # 2. Process with YOLO model
    # 3. Return detected bird tags
    return

# Decimal encoder for DynamoDB responses
class DecimalEncoder(json.JSONEncoder):
    def default(self, o):
        if isinstance(o, Decimal):
            return float(o)
        return super(DecimalEncoder, self).default(o)
