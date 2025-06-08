import pytest
import os
from moto import mock_dynamodb
import boto3
from src.handlers.tag_handler import lambda_handler

DYNAMODB_TABLE = "MediaMetadataTable"
os.environ["DYNAMODB_TABLE"] = DYNAMODB_TABLE

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
        table.put_item(Item={"fileKey": "test.jpg", "tags": ["crow"]})
        yield table

def test_add_tag(dynamodb):
    event = {
        "httpMethod": "POST",
        "body": '{"url": ["test.jpg"], "operation": 1, "tags": ["pigeon,2"]}'
    }
    response = lambda_handler(event, {})
    assert response["statusCode"] == 200

def test_remove_tag(dynamodb):
    event = {
        "httpMethod": "POST",
        "body": '{"url": ["test.jpg"], "operation": 0, "tags": ["crow,1"]}'
    }
    response = lambda_handler(event, {})
    assert response["statusCode"] == 200
