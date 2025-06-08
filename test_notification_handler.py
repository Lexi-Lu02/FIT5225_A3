import pytest
import os
from moto import mock_sns, mock_dynamodb
import boto3
from src.handlers.sns_handler import lambda_handler

SNS_TOPIC = "arn:aws:sns:us-east-1:123456789012:TestTopic"
os.environ["SNS_TOPIC"] = SNS_TOPIC

@pytest.fixture
def sns():
    with mock_sns():
        sns = boto3.client("sns", region_name="us-east-1")
        sns.create_topic(Name="TestTopic")
        yield sns

def test_subscribe(sns):
    event = {
        "path": "/v1/subscribe",
        "httpMethod": "POST",
        "body": '{"email": "test@example.com", "species": "crow"}'
    }
    response = lambda_handler(event, {})
    assert response["statusCode"] == 200

def test_unsubscribe(sns):
    # First, subscribe
    event = {
        "path": "/v1/subscribe",
        "httpMethod": "POST",
        "body": '{"email": "test@example.com", "species": "crow"}'
    }
    lambda_handler(event, {})
    # Now, unsubscribe
    event = {
        "path": "/v1/unsubscribe",
        "httpMethod": "POST",
        "body": '{"email": "test@example.com", "species": "crow"}'
    }
    response = lambda_handler(event, {})
    assert response["statusCode"] == 200