import pytest
import json
import os
import tempfile
from PIL import Image
import numpy as np
from moto import mock_s3, mock_dynamodb
import boto3
from src.handlers.bird_detection_lambda import lambda_handler
from src.utils.error_utils import BirdTagError, ErrorCode

# Test configuration
TEST_BUCKET = "test-bucket"
TEST_REGION = "us-east-1"
MODEL_BUCKET = "model-bucket"
MODEL_KEY = "model.pt"
MEDIA_BUCKET = "media-bucket"
DYNAMODB_TABLE = "BirdTagMedia"
CACHE_TTL = 3600
MAX_RETRIES = 3
CONFIDENCE_THRESHOLD = 0.5

# Set environment variables at module level
os.environ["AWS_ACCESS_KEY_ID"] = "testing"
os.environ["AWS_SECRET_ACCESS_KEY"] = "testing"
os.environ["AWS_SECURITY_TOKEN"] = "testing"
os.environ["AWS_SESSION_TOKEN"] = "testing"
os.environ["AWS_DEFAULT_REGION"] = TEST_REGION
os.environ["MODEL_BUCKET"] = MODEL_BUCKET
os.environ["MODEL_KEY"] = MODEL_KEY
os.environ["MEDIA_BUCKET"] = MEDIA_BUCKET
os.environ["DYNAMODB_TABLE"] = DYNAMODB_TABLE
os.environ["CACHE_TTL"] = str(CACHE_TTL)
os.environ["MAX_RETRIES"] = str(MAX_RETRIES)
os.environ["CONFIDENCE_THRESHOLD"] = str(CONFIDENCE_THRESHOLD)

@pytest.fixture
def aws_credentials():
    """Mocked AWS Credentials for moto."""
    # Environment variables are already set at module level
    pass

@pytest.fixture
def s3(aws_credentials):
    """Create mock S3 bucket."""
    with mock_s3():
        s3 = boto3.client("s3", region_name=TEST_REGION)
        # Create test buckets
        s3.create_bucket(Bucket=TEST_BUCKET)
        s3.create_bucket(Bucket=MODEL_BUCKET)
        s3.create_bucket(Bucket=MEDIA_BUCKET)
        
        # Upload mock model file
        with tempfile.NamedTemporaryFile() as tmp:
            tmp.write(b"mock model data")
            tmp.flush()
            s3.upload_file(tmp.name, MODEL_BUCKET, MODEL_KEY)
        
        yield s3

@pytest.fixture
def dynamodb(aws_credentials):
    """Create mock DynamoDB table."""
    with mock_dynamodb():
        dynamodb = boto3.resource("dynamodb", region_name=TEST_REGION)
        table = dynamodb.create_table(
            TableName=DYNAMODB_TABLE,
            KeySchema=[{"AttributeName": "fileKey", "KeyType": "HASH"}],
            AttributeDefinitions=[{"AttributeName": "fileKey", "AttributeType": "S"}],
            ProvisionedThroughput={"ReadCapacityUnits": 5, "WriteCapacityUnits": 5},
        )
        yield table

def create_test_image(width=800, height=600):
    """Create a test image file."""
    with tempfile.NamedTemporaryFile(suffix=".jpg", delete=False) as tmp:
        img = Image.new("RGB", (width, height), color="red")
        img.save(tmp.name, "JPEG")
        return tmp.name

def test_bird_detection(s3, dynamodb):
    """Test bird detection functionality."""
    # Create and upload test image
    test_image = create_test_image()
    s3.upload_file(test_image, MEDIA_BUCKET, "test.jpg")
    
    # Test detection
    event = {
        "httpMethod": "POST",
        "body": json.dumps({
            "bucket": MEDIA_BUCKET,
            "key": "test.jpg"
        })
    }
    response = lambda_handler(event, {})
    assert response["statusCode"] == 200
    body = json.loads(response["body"])
    assert "detections" in body
    assert "species" in body
    assert "confidence" in body
    
    # Cleanup
    os.unlink(test_image)

def test_detection_cache(s3, dynamodb):
    """Test detection caching functionality."""
    # Create and upload test image
    test_image = create_test_image()
    s3.upload_file(test_image, MEDIA_BUCKET, "test.jpg")
    
    # First request
    event = {
        "httpMethod": "POST",
        "body": json.dumps({
            "bucket": MEDIA_BUCKET,
            "key": "test.jpg"
        })
    }
    response1 = lambda_handler(event, {})
    assert response1["statusCode"] == 200
    
    # Second request (should use cache)
    response2 = lambda_handler(event, {})
    assert response2["statusCode"] == 200
    assert response1["body"] == response2["body"]
    
    # Cleanup
    os.unlink(test_image)

def test_invalid_image(s3, dynamodb):
    """Test handling of invalid images."""
    event = {
        "httpMethod": "POST",
        "body": json.dumps({
            "bucket": MEDIA_BUCKET,
            "key": "test.txt"
        })
    }
    response = lambda_handler(event, {})
    assert response["statusCode"] == 400
    body = json.loads(response["body"])
    assert "error" in body
    assert "invalid image" in body["error"]["message"].lower()

def test_missing_file(s3, dynamodb):
    """Test handling of missing files."""
    event = {
        "httpMethod": "POST",
        "body": json.dumps({
            "bucket": MEDIA_BUCKET,
            "key": "nonexistent.jpg"
        })
    }
    response = lambda_handler(event, {})
    assert response["statusCode"] == 404
    body = json.loads(response["body"])
    assert "error" in body
    assert "file not found" in body["error"]["message"].lower()

def test_model_error(s3, dynamodb):
    """Test model error handling."""
    # Create a corrupted image
    with tempfile.NamedTemporaryFile(suffix=".jpg", delete=False) as tmp:
        tmp.write(b"corrupted image data")
        corrupted_image = tmp.name
    
    s3.upload_file(corrupted_image, MEDIA_BUCKET, "corrupted.jpg")
    
    event = {
        "httpMethod": "POST",
        "body": json.dumps({
            "bucket": MEDIA_BUCKET,
            "key": "corrupted.jpg"
        })
    }
    response = lambda_handler(event, {})
    assert response["statusCode"] == 500
    body = json.loads(response["body"])
    assert "error" in body
    assert "model error" in body["error"]["message"].lower()
    
    # Cleanup
    os.unlink(corrupted_image) 