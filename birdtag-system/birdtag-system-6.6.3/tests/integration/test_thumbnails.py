import pytest
import os
import tempfile
from moto import mock_s3, mock_dynamodb
import boto3
from PIL import Image
from src.handlers.thumbnail_handler import lambda_handler

MEDIA_BUCKET = "media-bucket"
DYNAMODB_TABLE = "MediaMetadataTable"
os.environ["MEDIA_BUCKET"] = MEDIA_BUCKET
os.environ["DYNAMODB_TABLE"] = DYNAMODB_TABLE

@pytest.fixture
def s3():
    with mock_s3():
        s3 = boto3.client("s3", region_name="us-east-1")
        s3.create_bucket(Bucket=MEDIA_BUCKET)
        yield s3

@pytest.fixture
def dynamodb():
    with mock_dynamodb():
        dynamodb = boto3.resource("dynamodb", region_name="us-east-1")
        table = dynamodb.create_table(
            TableName=DYNAMODB_TABLE,
            KeySchema=[{"AttributeName": "fileKey", "KeyType": "HASH"}],
            AttributeDefinitions=[{"AttributeName": "fileKey", "AttributeType": "S"}],
            BillingMode="PAY_PER_REQUEST"
        )
        table.put_item(Item={"fileKey": "uploads/test.jpg"})
        yield table

def test_thumbnail_lambda_creates_thumbnail(s3, dynamodb):
    # Create and upload a test image
    with tempfile.NamedTemporaryFile(suffix=".jpg") as tmp:
        img = Image.new("RGB", (800, 600), color="blue")
        img.save(tmp.name, "JPEG")
        s3.upload_file(tmp.name, MEDIA_BUCKET, "uploads/test.jpg")

    # Simulate S3 event
    event = {
        "Records": [{
            "s3": {
                "bucket": {"name": MEDIA_BUCKET},
                "object": {"key": "uploads/test.jpg"}
            }
        }]
    }
    response = lambda_handler(event, {})
    assert response["statusCode"] == 200
    # Optionally, check that the thumbnail exists in S3
    result = s3.list_objects_v2(Bucket=MEDIA_BUCKET, Prefix="thumbnails/")
    assert "Contents" in result
    assert any(obj["Key"].endswith("test.jpg") for obj in result["Contents"])
