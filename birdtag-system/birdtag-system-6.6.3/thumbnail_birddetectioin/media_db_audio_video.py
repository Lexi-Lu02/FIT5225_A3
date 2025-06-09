# Lambda handler for processing AUDIO or VIDEO detection result and writing to BirdTagMedia

import boto3
import os
import json
from datetime import datetime
from uuid import uuid4

dynamodb = boto3.resource('dynamodb')
table = dynamodb.Table(os.environ['DDB_TABLE_NAME'])

def lambda_handler(event, context):
    try:
        file_type = event.get("file_type")  # 'audio' or 'video'
        user_id = event.get("user_id")
        s3_path = event.get("s3_path")
        file_key = event.get("file_key")
        thumbnail_path = event.get("thumbnail_path", "")
        detections = event.get("detections", [])  # audio: detection_segments, video: detection_boxes + frames

        if not file_type or not user_id or not s3_path or not file_key:
            return {"statusCode": 400, "body": json.dumps({"error": "Missing required metadata"})}

        now = datetime.utcnow().isoformat()
        media_id = str(uuid4())

        # Initialize base item
        item = {
            "id": media_id,
            "user_id": user_id,
            "file_type": file_type,
            "s3_path": s3_path,
            "thumbnail_path": thumbnail_path if file_type in ["image", "video"] else "",
            "created_at": now,
            "detected_species": [],
            "detection_segments": [],
            "detection_boxes": [],
            "detection_frames": []
        }

        # AUDIO mode (BirdNET output)
        if file_type == "audio":
            item["detection_segments"] = detections
            species_list = list(set([d["species"] for d in detections]))
            item["detected_species"] = species_list

        # VIDEO mode (YOLO output)
        elif file_type == "video":
            item["detection_boxes"] = detections.get("boxes", [])
            item["detection_frames"] = detections.get("frames", [])
            species_list = list(set([box["class_name"] for box in detections.get("boxes", [])]))
            item["detected_species"] = species_list

        else:
            return {"statusCode": 400, "body": json.dumps({"error": "Unsupported file_type"})}

        table.put_item(Item=item)

        return {
            "statusCode": 200,
            "body": json.dumps({"message": f"{file_type} metadata stored", "id": media_id})
        }

    except Exception as e:
        return {"statusCode": 500, "body": json.dumps({"error": str(e)})}
