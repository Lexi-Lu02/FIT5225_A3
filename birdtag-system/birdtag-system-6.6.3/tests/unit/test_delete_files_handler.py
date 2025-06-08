import pytest
import os
from moto import mock_s3, mock_dynamodb
import boto3
from src.handlers.media_processor_handler import lambda_handler

MEDIA_BUCKET = "media-bucket"
DYNAMODB_TABLE = "MediaMetadataTable"
os.environ["MEDIA_BUCKET"] = MEDIA_BUCKET
os.environ["DYNAMODB_TABLE"] = DYNAMODB_TABLE

@pytest.fixture
def s3():
    with mock_s3():
        s3 = boto3.client("s3", region_name="us-east-1")
        s3.create_bucket(Bucket=MEDIA_BUCKET)
        s3.put_object(Bucket=MEDIA_BUCKET, Key="uploads/test.jpg", Body=b"data")
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

def test_delete_file(s3, dynamodb):
    event = {
        "httpMethod": "POST",
        "body": '{"urls": ["uploads/test.jpg"]}'
    }
    response = lambda_handler(event, {})
    assert response["statusCode"] == 200
