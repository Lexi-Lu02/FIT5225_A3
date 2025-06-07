import pytest
import json
from src.handlers.auth_handler import lambda_handler
from src.utils.error_utils import BirdTagError, ErrorCode

def test_register_user(cognito):
    # Test user registration
    event = {
        "httpMethod": "POST",
        "body": json.dumps({
            "email": "test@example.com",
            "password": "Test123!",
            "given_name": "Test",
            "family_name": "User"
        })
    }
    response = lambda_handler(event, {})
    assert response["statusCode"] == 200
    body = json.loads(response["body"])
    assert "userId" in body
    assert "message" in body

def test_login_user(cognito):
    # Test user login
    event = {
        "httpMethod": "POST",
        "body": json.dumps({
            "email": "test@example.com",
            "password": "Test123!"
        })
    }
    response = lambda_handler(event, {})
    assert response["statusCode"] == 200
    body = json.loads(response["body"])
    assert "accessToken" in body
    assert "idToken" in body
    assert "refreshToken" in body

def test_verify_token(cognito):
    # Test token verification
    event = {
        "httpMethod": "POST",
        "body": json.dumps({
            "token": "test-token"
        })
    }
    response = lambda_handler(event, {})
    assert response["statusCode"] == 200
    body = json.loads(response["body"])
    assert "isValid" in body

def test_invalid_credentials(cognito):
    # Test invalid login credentials
    event = {
        "httpMethod": "POST",
        "body": json.dumps({
            "email": "test@example.com",
            "password": "WrongPassword123!"
        })
    }
    response = lambda_handler(event, {})
    assert response["statusCode"] == 401
    body = json.loads(response["body"])
    assert "error" in body

def test_invalid_registration(cognito):
    # Test invalid registration data
    event = {
        "httpMethod": "POST",
        "body": json.dumps({
            "email": "invalid-email",
            "password": "short",
            "given_name": "Test",
            "family_name": "User"
        })
    }
    response = lambda_handler(event, {})
    assert response["statusCode"] == 400
    body = json.loads(response["body"])
    assert "error" in body 