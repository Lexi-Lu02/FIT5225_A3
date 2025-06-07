import pytest
import json
from src.handlers.bird_detection_lambda import lambda_handler as detection_handler
from src.handlers.birdnet_analyzer_lambda import lambda_handler as analyzer_handler
from src.utils.error_utils import BirdTagError, ErrorCode

def test_bird_detection(s3, dynamodb):
    # Test bird detection
    event = {
        "httpMethod": "POST",
        "body": json.dumps({
            "fileKey": "test.jpg"
        })
    }
    response = detection_handler(event, {})
    assert response["statusCode"] == 200
    body = json.loads(response["body"])
    assert "detections" in body
    assert "species" in body
    assert "confidence" in body

def test_bird_sound_analysis(s3, dynamodb):
    # Test bird sound analysis
    event = {
        "httpMethod": "POST",
        "body": json.dumps({
            "fileKey": "test.wav"
        })
    }
    response = analyzer_handler(event, {})
    assert response["statusCode"] == 200
    body = json.loads(response["body"])
    assert "detections" in body
    assert "species" in body
    assert "confidence" in body

def test_detection_cache(s3, dynamodb):
    # Test detection caching
    # First request
    event = {
        "httpMethod": "POST",
        "body": json.dumps({
            "fileKey": "test.jpg"
        })
    }
    response1 = detection_handler(event, {})
    assert response1["statusCode"] == 200
    
    # Second request (should use cache)
    response2 = detection_handler(event, {})
    assert response2["statusCode"] == 200
    assert response1["body"] == response2["body"]

def test_analysis_cache(s3, dynamodb):
    # Test analysis caching
    # First request
    event = {
        "httpMethod": "POST",
        "body": json.dumps({
            "fileKey": "test.wav"
        })
    }
    response1 = analyzer_handler(event, {})
    assert response1["statusCode"] == 200
    
    # Second request (should use cache)
    response2 = analyzer_handler(event, {})
    assert response2["statusCode"] == 200
    assert response1["body"] == response2["body"]

def test_invalid_image(s3, dynamodb):
    # Test invalid image
    event = {
        "httpMethod": "POST",
        "body": json.dumps({
            "fileKey": "test.txt"
        })
    }
    response = detection_handler(event, {})
    assert response["statusCode"] == 400
    body = json.loads(response["body"])
    assert "error" in body

def test_invalid_audio(s3, dynamodb):
    # Test invalid audio
    event = {
        "httpMethod": "POST",
        "body": json.dumps({
            "fileKey": "test.txt"
        })
    }
    response = analyzer_handler(event, {})
    assert response["statusCode"] == 400
    body = json.loads(response["body"])
    assert "error" in body

def test_model_error(s3, dynamodb):
    # Test model error handling
    event = {
        "httpMethod": "POST",
        "body": json.dumps({
            "fileKey": "corrupted.jpg"
        })
    }
    response = detection_handler(event, {})
    assert response["statusCode"] == 500
    body = json.loads(response["body"])
    assert "error" in body 