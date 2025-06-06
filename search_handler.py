import json
import boto3
from boto3.dynamodb.conditions import Key, Attr
import base64
import os
from decimal import Decimal

dynamodb = boto3.resource('dynamodb')
TABLE_NAME = os.environ['DYNAMODB_TABLE']
MEDIA_BUCKET = os.environ['MEDIA_BUCKET']

def lambda_handler(event, context):
    """Handle different types of search queries"""
    try:
        path = event['path']
        
        if path == '/v1/search/tags':
            return search_by_tags(event)
        elif path == '/v1/search/species':
            return search_by_species(event)
        elif path == '/v1/search/thumbnails':
            return search_by_thumbnails(event)
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
    """Search files by bird tags with minimum counts"""
    try:
        body = json.loads(event['body'])
        
        # Parse search criteria
        search_criteria = {}
        if 'tags' in body:
            for bird, count in body['tags'].items():
                if isinstance(count, int):
                    search_criteria[bird] = count
                else:
                    search_criteria[bird] = int(count) if count else 1
        
        # Query database
        table = dynamodb.Table(TABLE_NAME)
        
        # Build filter expression
        filter_expressions = []
        expression_attr_values = {}
        expression_attr_names = {}
        
        # Add status filter
        filter_expressions.append('#status = :status')
        expression_attr_values[':status'] = 'completed'
        expression_attr_names['#status'] = 'status'
        
        # Add tags filter if criteria exist
        if search_criteria:
            filter_expressions.append('attribute_exists(tags)')
        
        # Combine filter expressions
        filter_expression = ' AND '.join(filter_expressions)
        
        # Scan with filter
        response = table.scan(
            FilterExpression=filter_expression,
            ExpressionAttributeValues=expression_attr_values,
            ExpressionAttributeNames=expression_attr_names
        )
        items = response['Items']
        
        # Continue scanning if there are more items
        while 'LastEvaluatedKey' in response:
            response = table.scan(
                FilterExpression=filter_expression,
                ExpressionAttributeValues=expression_attr_values,
                ExpressionAttributeNames=expression_attr_names,
                ExclusiveStartKey=response['LastEvaluatedKey']
            )
            items.extend(response['Items'])
        
        # Filter and process results
        matching_files = []
        for item in items:
            if not item.get('tags'):
                continue
                
            if matches_criteria(item['tags'], search_criteria):
                file_url = item.get('fileUrl', '')
                matching_files.append({
                    'fileUrl': file_url,
                    'fileKey': item.get('fileKey', ''),
                    'tags': item.get('tags', [])
                })
        
        return {
            'statusCode': 200,
            'headers': {
                'Content-Type': 'application/json',
                'Access-Control-Allow-Origin': '*',
                'Access-Control-Allow-Headers': 'Content-Type,Authorization',
                'Access-Control-Allow-Methods': 'OPTIONS,POST,GET'
            },
            'body': json.dumps({
                'results': matching_files
            }, cls=DecimalEncoder)
        }
        
    except Exception as e:
        print(f"Search by tags error: {str(e)}")
        return {
            'statusCode': 500,
            'headers': {
                'Content-Type': 'application/json',
                'Access-Control-Allow-Origin': '*'
            },
            'body': json.dumps({'error': str(e)})
        }

def search_by_species(event):
    """Search files by species names"""
    try:
        body = json.loads(event['body'])
        
        # Parse species search
        search_species = set()
        if 'species' in body:
            search_species = set(body['species'])
        
        # Query database
        table = dynamodb.Table(TABLE_NAME)
        
        # Build filter expression
        filter_expressions = []
        expression_attr_values = {}
        expression_attr_names = {}
        
        # Add status filter
        filter_expressions.append('#status = :status')
        expression_attr_values[':status'] = 'completed'
        expression_attr_names['#status'] = 'status'
        
        # Add tags filter
        filter_expressions.append('attribute_exists(tags)')
        
        # Combine filter expressions
        filter_expression = ' AND '.join(filter_expressions)
        
        # Scan with filter
        response = table.scan(
            FilterExpression=filter_expression,
            ExpressionAttributeValues=expression_attr_values,
            ExpressionAttributeNames=expression_attr_names
        )
        items = response['Items']
        
        # Continue scanning if there are more items
        while 'LastEvaluatedKey' in response:
            response = table.scan(
                FilterExpression=filter_expression,
                ExpressionAttributeValues=expression_attr_values,
                ExpressionAttributeNames=expression_attr_names,
                ExclusiveStartKey=response['LastEvaluatedKey']
            )
            items.extend(response['Items'])
        
        # Filter and process results
        matching_files = []
        for item in items:
            if not item.get('tags'):
                continue
                
            if has_any_matching_species(item['tags'], search_species):
                file_url = item.get('fileUrl', '')
                matching_files.append({
                    'fileUrl': file_url,
                    'fileKey': item.get('fileKey', ''),
                    'tags': item.get('tags', [])
                })
        
        return {
            'statusCode': 200,
            'headers': {
                'Content-Type': 'application/json',
                'Access-Control-Allow-Origin': '*',
                'Access-Control-Allow-Headers': 'Content-Type,Authorization',
                'Access-Control-Allow-Methods': 'OPTIONS,POST,GET'
            },
            'body': json.dumps({
                'results': matching_files
            }, cls=DecimalEncoder)
        }
        
    except Exception as e:
        print(f"Search by species error: {str(e)}")
        return {
            'statusCode': 500,
            'headers': {
                'Content-Type': 'application/json',
                'Access-Control-Allow-Origin': '*'
            },
            'body': json.dumps({'error': str(e)})
        }

def search_by_thumbnails(event):
    """Search files with available thumbnails"""
    try:
        # Query database
        table = dynamodb.Table(TABLE_NAME)
        
        # Build filter expression
        filter_expressions = []
        expression_attr_values = {}
        expression_attr_names = {}
        
        # Add status filter
        filter_expressions.append('#status = :status')
        expression_attr_values[':status'] = 'completed'
        expression_attr_names['#status'] = 'status'
        
        # Add thumbnail filter
        filter_expressions.append('attribute_exists(thumbnailUrl)')
        
        # Combine filter expressions
        filter_expression = ' AND '.join(filter_expressions)
        
        # Scan with filter
        response = table.scan(
            FilterExpression=filter_expression,
            ExpressionAttributeValues=expression_attr_values,
            ExpressionAttributeNames=expression_attr_names
        )
        items = response['Items']
        
        # Continue scanning if there are more items
        while 'LastEvaluatedKey' in response:
            response = table.scan(
                FilterExpression=filter_expression,
                ExpressionAttributeValues=expression_attr_values,
                ExpressionAttributeNames=expression_attr_names,
                ExclusiveStartKey=response['LastEvaluatedKey']
            )
            items.extend(response['Items'])
        
        # Process results
        matching_files = []
        for item in items:
            file_url = item.get('fileUrl', '')
            thumbnail_url = item.get('thumbnailUrl', '')
            
            if thumbnail_url:
                matching_files.append({
                    'thumbnailUrl': thumbnail_url,
                    'fileUrl': file_url,
                    'fileKey': item.get('fileKey', ''),
                    'tags': item.get('tags', [])
                })
        
        return {
            'statusCode': 200,
            'headers': {
                'Content-Type': 'application/json',
                'Access-Control-Allow-Origin': '*',
                'Access-Control-Allow-Headers': 'Content-Type,Authorization',
                'Access-Control-Allow-Methods': 'OPTIONS,POST,GET'
            },
            'body': json.dumps({
                'results': matching_files
            }, cls=DecimalEncoder)
        }
        
    except Exception as e:
        print(f"Search by thumbnails error: {str(e)}")
        return {
            'statusCode': 500,
            'headers': {
                'Content-Type': 'application/json',
                'Access-Control-Allow-Origin': '*'
            },
            'body': json.dumps({'error': str(e)})
        }

def search_by_file(event):
    """Search by tags provided for an uploaded file and find similar tagged files"""
    try:
        body = json.loads(event['body'])
        
        # Expecting tags in the request body
        search_tags = set()
        if 'tags' in body:
            search_tags = set(body['tags'])  # e.g., ["crow", "pigeon"]
        else:
            return {
                'statusCode': 400,
                'headers': {
                    'Content-Type': 'application/json',
                    'Access-Control-Allow-Origin': '*'
                },
                'body': json.dumps({'error': 'No tags provided for search'})
            }
        
        # Query database
        table = dynamodb.Table(TABLE_NAME)
        filter_expressions = []
        expression_attr_values = {}
        expression_attr_names = {}
        
        filter_expressions.append('#status = :status')
        expression_attr_values[':status'] = 'completed'
        expression_attr_names['#status'] = 'status'
        filter_expressions.append('attribute_exists(tags)')
        filter_expression = ' AND '.join(filter_expressions)
        
        response = table.scan(
            FilterExpression=filter_expression,
            ExpressionAttributeValues=expression_attr_values,
            ExpressionAttributeNames=expression_attr_names
        )
        items = response['Items']
        
        # Continue scanning if there are more items
        while 'LastEvaluatedKey' in response:
            response = table.scan(
                FilterExpression=filter_expression,
                ExpressionAttributeValues=expression_attr_values,
                ExpressionAttributeNames=expression_attr_names,
                ExclusiveStartKey=response['LastEvaluatedKey']
            )
            items.extend(response['Items'])
        
        # Find files with ANY of these tags/species
        matching_files = []
        for item in items:
            if not item.get('tags'):
                continue
            if has_any_matching_species(item['tags'], search_tags):
                file_url = item.get('fileUrl', '')
                thumbnail_url = item.get('thumbnailUrl', '')
                matching_files.append({
                    'fileUrl': file_url,
                    'thumbnailUrl': thumbnail_url,
                    'fileKey': item.get('fileKey', ''),
                    'tags': item.get('tags', [])
                })
        
        return {
            'statusCode': 200,
            'headers': {
                'Content-Type': 'application/json',
                'Access-Control-Allow-Origin': '*',
                'Access-Control-Allow-Headers': 'Content-Type,Authorization',
                'Access-Control-Allow-Methods': 'OPTIONS,POST'
            },
            'body': json.dumps({
                'results': matching_files
            }, cls=DecimalEncoder)
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

# Decimal encoder for DynamoDB responses
class DecimalEncoder(json.JSONEncoder):
    def default(self, o):
        if isinstance(o, Decimal):
            return float(o)
        return super(DecimalEncoder, self).default(o)
