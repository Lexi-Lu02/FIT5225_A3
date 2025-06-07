import pytest
import json
import os
import tempfile
from moto import mock_s3
import boto3
from src.handlers.ffmpeg_handler import lambda_handler
from src.utils.error_utils import BirdTagError, ErrorCode

# Test configuration
TEST_BUCKET = "test-bucket"
TEST_REGION = "us-east-1"

@pytest.fixture
def aws_credentials():
    """Mocked AWS Credentials for moto."""
    os.environ["AWS_ACCESS_KEY_ID"] = "testing"
    os.environ["AWS_SECRET_ACCESS_KEY"] = "testing"
    os.environ["AWS_SECURITY_TOKEN"] = "testing"
    os.environ["AWS_SESSION_TOKEN"] = "testing"
    os.environ["AWS_DEFAULT_REGION"] = TEST_REGION

@pytest.fixture
def s3(aws_credentials):
    """Create mock S3 bucket."""
    with mock_s3():
        s3 = boto3.client("s3", region_name=TEST_REGION)
        s3.create_bucket(Bucket=TEST_BUCKET)
        yield s3

def create_test_video():
    """Create a test video file."""
    with tempfile.NamedTemporaryFile(suffix=".mp4", delete=False) as tmp:
        tmp.write(b"fake video content")
        return tmp.name

def create_test_audio():
    """Create a test audio file."""
    with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmp:
        tmp.write(b"fake audio content")
        return tmp.name

def test_video_thumbnail(s3):
    """Test video thumbnail generation."""
    # Create and upload test video
    test_video = create_test_video()
    s3.upload_file(test_video, TEST_BUCKET, "test.mp4")
    
    # Test thumbnail generation
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
    assert "thumbnailUrl" in body
    assert "thumbnailKey" in body
    
    # Verify thumbnail exists in S3
    thumbnail_key = body["thumbnailKey"]
    response = s3.head_object(Bucket=TEST_BUCKET, Key=thumbnail_key)
    assert response["ContentType"] == "image/jpeg"
    
    # Cleanup
    os.unlink(test_video)

def test_audio_waveform(s3):
    """Test audio waveform generation."""
    # Create and upload test audio
    test_audio = create_test_audio()
    s3.upload_file(test_audio, TEST_BUCKET, "test.wav")
    
    # Test waveform generation
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
    
    # Verify waveform exists in S3
    waveform_key = body["waveformKey"]
    response = s3.head_object(Bucket=TEST_BUCKET, Key=waveform_key)
    assert response["ContentType"] == "image/png"
    
    # Cleanup
    os.unlink(test_audio)

def test_invalid_timestamp(s3):
    """Test handling of invalid timestamps."""
    # Create and upload test video
    test_video = create_test_video()
    s3.upload_file(test_video, TEST_BUCKET, "test.mp4")
    
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
    assert "invalid timestamp" in body["error"]["message"].lower()
    
    # Cleanup
    os.unlink(test_video)

def test_missing_file(s3):
    """Test handling of missing files."""
    event = {
        "httpMethod": "POST",
        "body": json.dumps({
            "fileKey": "nonexistent.mp4"
        })
    }
    response = lambda_handler(event, {})
    assert response["statusCode"] == 404
    body = json.loads(response["body"])
    assert "error" in body
    assert "file not found" in body["error"]["message"].lower()

def test_invalid_media_type(s3):
    """Test handling of invalid media types."""
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
    assert "invalid media type" in body["error"]["message"].lower() 