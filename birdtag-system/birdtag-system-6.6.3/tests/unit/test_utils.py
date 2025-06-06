import pytest
from src.utils.error_utils import BirdTagError, ErrorCode
from src.utils.s3_utils import get_content_type
from src.utils.dynamo_utils import create_media_record
from src.utils.image_utils import is_valid_image
from src.utils.audio_utils import is_valid_audio

def test_birdtag_error():
    error = BirdTagError(
        message="Test error",
        error_code=ErrorCode.UNKNOWN_ERROR,
        status_code=500
    )
    assert str(error) == "Test error"
    assert error.error_code == ErrorCode.UNKNOWN_ERROR
    assert error.status_code == 500

def test_get_content_type():
    assert get_content_type("test.jpg") == "image/jpeg"
    assert get_content_type("test.png") == "image/png"
    assert get_content_type("test.wav") == "audio/wav"
    assert get_content_type("test.mp3") == "audio/mpeg"

def test_is_valid_image():
    assert is_valid_image("test.jpg")
    assert is_valid_image("test.png")
    assert not is_valid_image("test.txt")
    assert not is_valid_image("test.wav")

def test_is_valid_audio():
    assert is_valid_audio("test.wav")
    assert is_valid_audio("test.mp3")
    assert not is_valid_audio("test.txt")
    assert not is_valid_audio("test.jpg") 