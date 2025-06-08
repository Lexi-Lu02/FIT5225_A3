import boto3
import json
import os
from datetime import datetime
import uuid

# Initialise DynamoDB resources
dynamodb = boto3.resource('dynamodb')
table = dynamodb.Table(os.environ['DDB_TABLE_NAME'])

S3_UPLOAD_BUCKET = os.environ.get('S3_UPLOAD_BUCKET', '')
S3_THUMBNAIL_BUCKET = os.environ.get('S3_THUMBNAIL_BUCKET', '')

def lambda_handler(event, context):
    try:
        file_key = event.get("fileKey")
        tags_dict = event.get("tags", {})
        file_type = event.get("fileType", "audio")  # default to audio
        thumbnail = event.get("thumbnailUrl", "")  
        file_url = event.get("fileUrl", "")        
        source = event.get("source", "BirdNET")
        user_id = event.get("userId", "anonymous")  
        detection_segments = event.get("detectionSegments", [])

        # Auto-detect file type
        if file_key and file_key.lower().endswith(('.mp4', '.mov', '.avi', '.mkv')):
            file_type = "video"

        # Format tag array
        tags_array = [f"{k},{v}" for k, v in tags_dict.items()]
        detected_species = list(tags_dict.keys()) if tags_dict else []

        # Construct DynamoDB record
        item = {
            "id": str(uuid.uuid4()),
            "fileKey": file_key,
            "fileType": file_type,
            "fileUrl": file_url,
            "thumbnailUrl": thumbnail,
            "tags": tags_array,
            "detected_species": detected_species,
            "detection_segments": detection_segments,
            "user_id": user_id,
            "uploadTime": datetime.utcnow().isoformat(),
            "source": source,
            "status": "completed"
        }

        # Write to DynamoDB
        table.put_item(Item=item)

        return {
            "statusCode": 200,
            "body": json.dumps({
                "message": " Metadata stored successfully",
                "fileKey": file_key,
                "detected_species": detected_species
            })
        }

    except Exception as e:
        return {
            "statusCode": 500,
            "body": json.dumps({
                "error": "Failed to store metadata",
                "details": str(e)
            })
        }
