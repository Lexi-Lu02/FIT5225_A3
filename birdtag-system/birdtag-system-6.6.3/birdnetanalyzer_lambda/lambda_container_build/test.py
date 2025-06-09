import json
import os
from lambda_function import lambda_handler
from birdnet_analyzer.analyze import analyze

# Mock S3 event payload simulating AWS Lambda trigger
# This simulates an S3 object creation event that would trigger the Lambda function
MOCK_EVENT = {
    "Records": [
        {
            "s3": {
                "bucket": {"name": "test-bucket"},
                "object": {"key": "upload/audio/test_audio.wav"}
            }
        }
    ]
}

class MockContext:
    """
    Mock AWS Lambda context object for local testing.
    Implements essential context attributes required by AWS Lambda runtime.
    """
    function_name = "test_lambda"
    memory_limit_in_mb = 128
    invoked_function_arn = "arn:aws:lambda:us-east-1:123456789012:function:test_lambda"
    aws_request_id = "test-request-id"

if __name__ == "__main__":
    # Execute BirdNET analysis on test audio file
    # This step is optional and can be used to verify BirdNET functionality independently
    analyze(
        input="test_audio.wav",
        output="./test_output",
        min_conf=0.1,
        sensitivity=1.0,
        overlap=0.0,
        threads=1,
        batch_size=1,
        lat=None,
        lon=None,
        week=None
    )
    
    # Execute Lambda handler with mock event and context
    # Modify bucket/key or provide a local test audio file as needed
    response = lambda_handler(MOCK_EVENT, MockContext())
    
    # Print formatted Lambda response for debugging
    print("Lambda Response:")
    print(json.dumps(json.loads(response["body"]), indent=2, ensure_ascii=False))
    
    # Validate response payload structure
    # Check for required fields in the response body
    required_keys = ["message", "media_id", "detected_species", "detection_segments", "file_location", "created_at"]
    body = json.loads(response["body"])
    missing = [k for k in required_keys if k not in body]
    if missing:
        print(f"❌ Missing required fields: {missing}")
    else:
        print("✅ Response payload structure validation successful!") 
