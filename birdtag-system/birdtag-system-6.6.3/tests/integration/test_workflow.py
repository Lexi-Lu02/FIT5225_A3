import pytest
import json
import time
from src.handlers.auth_handler import lambda_handler as auth_handler
from src.handlers.upload_handler import lambda_handler as upload_handler
from src.handlers.media_processor_handler import lambda_handler as media_handler
from src.handlers.bird_detection_lambda import lambda_handler as detection_handler
from src.handlers.birdnet_analyzer_lambda import lambda_handler as analyzer_handler
from src.handlers.search_handler import lambda_handler as search_handler

def test_complete_workflow(s3, dynamodb, cognito):
    # 1. Register user
    register_event = {
        "httpMethod": "POST",
        "body": json.dumps({
            "email": "test@example.com",
            "password": "Test123!",
            "given_name": "Test",
            "family_name": "User"
        })
    }
    register_response = auth_handler(register_event, {})
    assert register_response["statusCode"] == 200
    register_body = json.loads(register_response["body"])
    assert "userId" in register_body

    # 2. Login user
    login_event = {
        "httpMethod": "POST",
        "body": json.dumps({
            "email": "test@example.com",
            "password": "Test123!"
        })
    }
    login_response = auth_handler(login_event, {})
    assert login_response["statusCode"] == 200
    login_body = json.loads(login_response["body"])
    assert "accessToken" in login_body
    token = login_body["accessToken"]

    # 3. Get upload URL
    upload_event = {
        "httpMethod": "GET",
        "queryStringParameters": {
            "fileType": "image/jpeg",
            "fileName": "test.jpg"
        },
        "headers": {
            "Authorization": f"Bearer {token}"
        }
    }
    upload_response = upload_handler(upload_event, {})
    assert upload_response["statusCode"] == 200
    upload_body = json.loads(upload_response["body"])
    assert "uploadUrl" in upload_body
    assert "fileKey" in upload_body
    file_key = upload_body["fileKey"]

    # 4. Process media
    media_event = {
        "httpMethod": "POST",
        "body": json.dumps({
            "fileKey": file_key
        }),
        "headers": {
            "Authorization": f"Bearer {token}"
        }
    }
    media_response = media_handler(media_event, {})
    assert media_response["statusCode"] == 200
    media_body = json.loads(media_response["body"])
    assert "thumbnailUrl" in media_body

    # 5. Run bird detection
    detection_event = {
        "httpMethod": "POST",
        "body": json.dumps({
            "fileKey": file_key
        }),
        "headers": {
            "Authorization": f"Bearer {token}"
        }
    }
    detection_response = detection_handler(detection_event, {})
    assert detection_response["statusCode"] == 200
    detection_body = json.loads(detection_response["body"])
    assert "detections" in detection_body

    # 6. Search for media
    search_event = {
        "httpMethod": "POST",
        "body": json.dumps({
            "query": "bird",
            "tags": ["nature"],
            "startDate": "2024-01-01",
            "endDate": "2024-12-31"
        }),
        "headers": {
            "Authorization": f"Bearer {token}"
        }
    }
    search_response = search_handler(search_event, {})
    assert search_response["statusCode"] == 200
    search_body = json.loads(search_response["body"])
    assert "results" in search_body

def test_audio_workflow(s3, dynamodb, cognito):
    # 1. Login user
    login_event = {
        "httpMethod": "POST",
        "body": json.dumps({
            "email": "test@example.com",
            "password": "Test123!"
        })
    }
    login_response = auth_handler(login_event, {})
    assert login_response["statusCode"] == 200
    login_body = json.loads(login_response["body"])
    token = login_body["accessToken"]

    # 2. Get upload URL for audio
    upload_event = {
        "httpMethod": "GET",
        "queryStringParameters": {
            "fileType": "audio/wav",
            "fileName": "test.wav"
        },
        "headers": {
            "Authorization": f"Bearer {token}"
        }
    }
    upload_response = upload_handler(upload_event, {})
    assert upload_response["statusCode"] == 200
    upload_body = json.loads(upload_response["body"])
    file_key = upload_body["fileKey"]

    # 3. Process audio
    media_event = {
        "httpMethod": "POST",
        "body": json.dumps({
            "fileKey": file_key
        }),
        "headers": {
            "Authorization": f"Bearer {token}"
        }
    }
    media_response = media_handler(media_event, {})
    assert media_response["statusCode"] == 200
    media_body = json.loads(media_response["body"])
    assert "waveformUrl" in media_body

    # 4. Run bird sound analysis
    analysis_event = {
        "httpMethod": "POST",
        "body": json.dumps({
            "fileKey": file_key
        }),
        "headers": {
            "Authorization": f"Bearer {token}"
        }
    }
    analysis_response = analyzer_handler(analysis_event, {})
    assert analysis_response["statusCode"] == 200
    analysis_body = json.loads(analysis_response["body"])
    assert "detections" in analysis_body

def test_error_handling(s3, dynamodb, cognito):
    # Test unauthorized access
    event = {
        "httpMethod": "GET",
        "queryStringParameters": {
            "fileType": "image/jpeg",
            "fileName": "test.jpg"
        }
    }
    response = upload_handler(event, {})
    assert response["statusCode"] == 401

    # Test invalid token
    event = {
        "httpMethod": "GET",
        "queryStringParameters": {
            "fileType": "image/jpeg",
            "fileName": "test.jpg"
        },
        "headers": {
            "Authorization": "Bearer invalid-token"
        }
    }
    response = upload_handler(event, {})
    assert response["statusCode"] == 401

    # Test invalid file type
    event = {
        "httpMethod": "GET",
        "queryStringParameters": {
            "fileType": "invalid/type",
            "fileName": "test.txt"
        },
        "headers": {
            "Authorization": "Bearer valid-token"
        }
    }
    response = upload_handler(event, {})
    assert response["statusCode"] == 400 