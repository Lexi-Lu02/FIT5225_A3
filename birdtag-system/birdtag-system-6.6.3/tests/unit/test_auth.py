import pytest
import json
import os
from src.handlers.auth_handler import lambda_handler, handle_login, handle_register, handle_verify
from src.utils.error_utils import BirdTagError, ErrorCode

@pytest.fixture
def register_event():
    """Generate Register Event"""
    return {
        'httpMethod': 'POST',
        'path': '/auth/register',
        'headers': {
            'Content-Type': 'application/json'
        },
        'body': json.dumps({
            'email': 'test@example.com',
            'password': 'Test123!',
            'name': 'Test User'
        })
    }

@pytest.fixture
def login_event():
    """Generate Login Event"""
    return {
        'httpMethod': 'POST',
        'path': '/auth/login',
        'headers': {
            'Content-Type': 'application/json'
        },
        'body': json.dumps({
            'email': 'test@example.com',
            'password': 'Test123!'
        })
    }

@pytest.fixture
def verify_event():
    """Generate Verify Event"""
    return {
        'httpMethod': 'POST',
        'path': '/auth/verify',
        'headers': {
            'Content-Type': 'application/json'
        },
        'body': json.dumps({
            'email': 'test@example.com',
            'code': '123456'
        })
    }

def test_register_user_success(register_event, local_mode):
    """Test successful user registration"""
    response = handle_register(register_event, None)
    assert response['statusCode'] == 200
    body = json.loads(response['body'])
    assert 'message' in body
    assert 'success' in body['message'].lower()

def test_register_user_invalid_email(register_event, local_mode):
    """Test registration with invalid email"""
    register_event['body'] = json.dumps({
        'email': 'invalid-email',
        'password': 'Test123!',
        'name': 'Test User'
    })
    response = handle_register(register_event, None)
    assert response['statusCode'] == 400
    body = json.loads(response['body'])
    assert 'error' in body

def test_register_user_short_password(register_event, local_mode):
    """Test registration with short password"""
    register_event['body'] = json.dumps({
        'email': 'test@example.com',
        'password': 'short',
        'name': 'Test User'
    })
    response = handle_register(register_event, None)
    assert response['statusCode'] == 400
    body = json.loads(response['body'])
    assert 'error' in body

def test_login_user_success(login_event, local_mode):
    """Test successful user login"""
    response = handle_login(login_event, None)
    assert response['statusCode'] == 200
    body = json.loads(response['body'])
    assert 'tokens' in body
    assert 'accessToken' in body['tokens']

def test_login_user_invalid_credentials(login_event, local_mode):
    """Test login with invalid credentials"""
    login_event['body'] = json.dumps({
        'email': 'test@example.com',
        'password': 'WrongPassword123!'
    })
    response = handle_login(login_event, None)
    assert response['statusCode'] == 401
    body = json.loads(response['body'])
    assert 'error' in body

def test_verify_email_success(verify_event, local_mode):
    """Test successful email verification"""
    response = handle_verify(verify_event, None)
    assert response['statusCode'] == 200
    body = json.loads(response['body'])
    assert 'message' in body
    assert 'success' in body['message'].lower()

def test_verify_email_invalid_code(verify_event, local_mode):
    """Test verification with invalid code"""
    verify_event['body'] = json.dumps({
        'email': 'test@example.com',
        'code': '000000'
    })
    response = handle_verify(verify_event, None)
    assert response['statusCode'] == 400
    body = json.loads(response['body'])
    assert 'error' in body

def test_missing_required_fields(register_event, local_mode):
    """Test registration with missing required fields"""
    register_event['body'] = json.dumps({
        'email': 'test@example.com'
        # Missing password and name
    })
    response = handle_register(register_event, None)
    assert response['statusCode'] == 400
    body = json.loads(response['body'])
    assert 'error' in body
    assert 'required' in body['error'].lower()

def test_invalid_content_type(register_event, local_mode):
    """Test request with invalid content type"""
    register_event['headers']['Content-Type'] = 'text/plain'
    response = lambda_handler(register_event, None)
    assert response['statusCode'] == 400
    body = json.loads(response['body'])
    assert 'error' in body
    assert 'content-type' in body['error']['message'].lower()

def test_cors_headers(register_event, local_mode):
    """Test CORS headers in response"""
    response = handle_register(register_event, None)
    assert 'Access-Control-Allow-Origin' in response['headers']
    assert 'Access-Control-Allow-Headers' in response['headers']
    assert 'Access-Control-Allow-Methods' in response['headers'] 