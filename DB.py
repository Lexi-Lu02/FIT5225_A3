import boto3
import json
import os
from datetime import datetime

# Initialise DynamoDB resources
dynamodb = boto3.resource('dynamodb')
table = dynamodb.Table(os.environ['DDB_TABLE_NAME'])

S3_UPLOAD_BUCKET = os.environ.get('S3_UPLOAD_BUCKET', '')
S3_THUMBNAIL_BUCKET = os.environ.get('S3_THUMBNAIL_BUCKET', '')

def lambda_handler(event, context):
    try:
        file_key = event["fileKey"]
        tags_dict = event.get("tags", {})
        file_type = event.get("fileType", "audio")  # default to audio unless otherwise detected
        thumbnail = event.get("thumbnailUrl", "")  
        file_url = event.get("fileUrl", "")        
        source = event.get("source", "BirdNET")

        # Auto-detect video file type based on file extension
        if file_key.lower().endswith(('.mp4', '.mov', '.avi', '.mkv')):
            file_type = "video"

        # Convert a dictionary of labels into an array, e.g. ['crow,3', 'owl,1']
        tags_array = [f"{k},{v}" for k, v in tags_dict.items()]

        # Constructing a record entry for DynamoDB to write to
        item = {
            "fileKey": file_key,
            "tags": tags_array,
            "fileType": file_type,
            "uploadTime": datetime.utcnow().isoformat(),
            "source": source,
            "status": "completed"
        }

        # Write if the event contains link information
        if file_url:
            item["fileUrl"] = file_url
        if thumbnail:
            item["thumbnailUrl"] = thumbnail

        # Perform a write operation
        table.put_item(Item=item)

        # Returns a successful write result
        return {
            "statusCode": 200,
            "body": json.dumps({
                "message": "Metadata stored successfully",
                "fileKey": file_key
            })
        }

    except Exception as e:
        # Error handling: return 500 and error details
        return {
            "statusCode": 500,
            "body": json.dumps({
                "error": "Failed to store metadata",
                "details": str(e)
            })
        }
