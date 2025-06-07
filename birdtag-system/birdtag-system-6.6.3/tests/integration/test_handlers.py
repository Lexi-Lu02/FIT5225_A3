import pytest
import json
from src.handlers.upload_handler import lambda_handler as upload_handler
from src.handlers.search_handler import lambda_handler as search_handler
from src.handlers.tag_handler import lambda_handler as tag_handler

def test_upload_handler(s3, dynamodb):
    # Test upload handler
    event = {
        "httpMethod": "GET",
        "queryStringParameters": {
            "fileType": "image/jpeg",
            "fileName": "test.jpg"
        }
    }
    response = upload_handler(event, {})
    assert response["statusCode"] == 200
    body = json.loads(response["body"])
    assert "uploadUrl" in body
    assert "fileKey" in body

def test_search_handler(dynamodb):
    # Test search handler
    event = {
        "httpMethod": "POST",
        "body": json.dumps({
            "query": "bird",
            "tags": ["nature"],
            "startDate": "2024-01-01",
            "endDate": "2024-12-31"
        })
    }
    response = search_handler(event, {})
    assert response["statusCode"] == 200
    body = json.loads(response["body"])
    assert "results" in body

def test_tag_handler(dynamodb):
    # Test tag handler
    event = {
        "httpMethod": "POST",
        "body": json.dumps({
            "fileKey": "test.jpg",
            "tags": ["bird", "nature"]
        })
    }
    response = tag_handler(event, {})
    assert response["statusCode"] == 200
    body = json.loads(response["body"])
    assert "message" in body 