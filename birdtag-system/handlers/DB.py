import boto3
import json
import os
import logging

# Initialize logger
logger = logging.getLogger()
logger.setLevel(logging.INFO)

# Initialise DynamoDB resources
dynamodb = boto3.resource('dynamodb')
table = dynamodb.Table(os.environ['DDB_TABLE_NAME'])

S3_UPLOAD_BUCKET = os.environ.get('S3_UPLOAD_BUCKET', '')
S3_THUMBNAIL_BUCKET = os.environ.get('S3_THUMBNAIL_BUCKET', '')

def lambda_handler(event, context):
    try:
        logger.info(f"Received event: {json.dumps(event)}")

        file_key = event.get("fileKey")
        if not file_key:
            return {
                "statusCode": 400,
                "body": json.dumps({"error": "Missing required field: fileKey"})
            }

        tags_dict = event.get("tags", {})
        file_type = event.get("fileType", "image")  # default to image
        thumbnail = event.get("thumbnailUrl", "")
        file_url = event.get("fileUrl", "")
        source = event.get("source", "BirdNET")

        # Auto-detect video file type based on file extension
        if file_key.lower().endswith(('.mp4', '.mov', '.avi', '.mkv')):
            file_type = "video"

        # Convert a dictionary of labels into an array, e.g. ['crow,0.86', 'owl,0.91']
        tags_array = [f"{k},{v}" for k, v in tags_dict.items()]

        # Compose item to store in DynamoDB
        item = {
            "fileKey": file_key,
            "fileUrl": file_url,
            "fileType": file_type,
            "thumbnailUrl": thumbnail,
            "tags": tags_array,
            "source": source
        }

        table.put_item(Item=item)
        logger.info(f"Successfully wrote metadata to DynamoDB for {file_key}")

        return {
            "statusCode": 200,
            "body": json.dumps({
                "message": "Successfully wrote metadata",
                "fileKey": file_key,
                "fileType": file_type,
                "tags": tags_array
            })
        }

    except Exception as e:
        logger.error(f"Error writing metadata: {str(e)}")
        return {
            "statusCode": 500,
            "body": json.dumps({"error": "Failed to store metadata", "details": str(e)})
        }


