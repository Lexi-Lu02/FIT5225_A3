import boto3
import os
import json
from datetime import datetime

# Initialize DynamoDB
TABLE_NAME = os.environ["DDB_TABLE_NAME"]
dynamodb = boto3.resource("dynamodb")
table = dynamodb.Table(TABLE_NAME)

def write_detection_result(file_key, tags, file_type, source, file_url="", thumbnail_url=""):
    tags_array = [f"{k},{v}" for k, v in tags.items()]

    item = {
        "fileKey": file_key,
        "tags": tags_array,
        "fileType": file_type,
        "uploadTime": datetime.utcnow().isoformat(),
        "source": source,
        "status": "completed"
    }

    if file_url:
        item["fileUrl"] = file_url
    if thumbnail_url:
        item["thumbnailUrl"] = thumbnail_url

    table.put_item(Item=item)

def lambda_handler(event, context):
    try:
        file_key = event["fileKey"]
        tags_dict = event.get("tags", {})
        file_type = event.get("fileType", "audio")
        file_url = event.get("fileUrl", "")
        thumbnail = event.get("thumbnailUrl", "")
        source = event.get("source", "BirdNET")

        write_detection_result(
            file_key=file_key,
            tags=tags_dict,
            file_type=file_type,
            source=source,
            file_url=file_url,
            thumbnail_url=thumbnail
        )

        return {
            "statusCode": 200,
            "body": json.dumps({
                "message": "Metadata stored successfully",
                "fileKey": file_key
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

