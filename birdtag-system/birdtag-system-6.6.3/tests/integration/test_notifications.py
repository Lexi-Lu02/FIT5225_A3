import pytest
import json
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

def test_subscribe_and_unsubscribe(sns):
    # Subscribe
    subscribe_event = {
        "path": "/v1/subscribe",
        "httpMethod": "POST",
        "body": json.dumps({"email": "test@example.com", "species": "crow"})
    }
    subscribe_response = lambda_handler(subscribe_event, {})
    assert subscribe_response["statusCode"] == 200
    assert "Subscribed" in subscribe_response["body"]

    # Unsubscribe
    unsubscribe_event = {
        "path": "/v1/unsubscribe",
        "httpMethod": "POST",
        "body": json.dumps({"email": "test@example.com", "species": "crow"})
    }
    unsubscribe_response = lambda_handler(unsubscribe_event, {})
    assert unsubscribe_response["statusCode"] == 200
    assert "Unsubscribed" in unsubscribe_response["body"]
