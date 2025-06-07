import pytest
import json
from src.handlers.media_processor_handler import lambda_handler
from src.handlers.thumbnail_handler import lambda_handler as thumbnail_handler
from src.utils.error_utils import BirdTagError, ErrorCode

def test_video_processing(s3):
    # Test video processing
    event = {
        "httpMethod": "POST",
        "body": json.dumps({
            "fileKey": "test.mp4",
            "timestamp": 5
        })
    }
    response = lambda_handler(event, {})
    assert response["statusCode"] == 200
    body = json.loads(response["body"])
    assert "previewUrl" in body
    assert "previewKey" in body

def test_audio_processing(s3):
    # Test audio processing
    event = {
        "httpMethod": "POST",
        "body": json.dumps({
            "fileKey": "test.wav"
        })
    }
    response = lambda_handler(event, {})
    assert response["statusCode"] == 200
    body = json.loads(response["body"])
    assert "waveformUrl" in body
    assert "waveformKey" in body

def test_thumbnail_generation(s3):
    # Test thumbnail generation
    event = {
        "httpMethod": "POST",
        "body": json.dumps({
            "fileKey": "test.jpg",
            "width": 200,
            "height": 200
        })
    }
    response = thumbnail_handler(event, {})
    assert response["statusCode"] == 200
    body = json.loads(response["body"])
    assert "thumbnailUrl" in body
    assert "thumbnailKey" in body

def test_invalid_media_type(s3):
    # Test invalid media type
    event = {
        "httpMethod": "POST",
        "body": json.dumps({
            "fileKey": "test.txt"
        })
    }
    response = lambda_handler(event, {})
    assert response["statusCode"] == 400
    body = json.loads(response["body"])
    assert "error" in body

def test_missing_file(s3):
    # Test missing file
    event = {
        "httpMethod": "POST",
        "body": json.dumps({
            "fileKey": "nonexistent.jpg"
        })
    }
    response = lambda_handler(event, {})
    assert response["statusCode"] == 404
    body = json.loads(response["body"])
    assert "error" in body

def test_invalid_timestamp(s3):
    # Test invalid timestamp
    event = {
        "httpMethod": "POST",
        "body": json.dumps({
            "fileKey": "test.mp4",
            "timestamp": -1
        })
    }
    response = lambda_handler(event, {})
    assert response["statusCode"] == 400
    body = json.loads(response["body"])
    assert "error" in body 