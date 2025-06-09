import os
import json
import boto3
from moto import mock_s3, mock_dynamodb
import pytest
from lambda_function import lambda_handler
import uuid
from datetime import datetime
from birdnet_analyzer.analyze import analyze
import argparse

# Helper function to create a mock S3 event
def create_s3_event(bucket, key):
    return {
        'Records': [{
            's3': {
                'bucket': {'name': bucket},
                'object': {'key': key}
            }
        }]
    }

@mock_s3
@mock_dynamodb
def run_mock_test():
    """Test the full lambda_function logic with mocked AWS services."""
    os.environ['DDB_TABLE'] = 'BirdTagMedia'
    os.environ['MODEL_PATH'] = './BirdNET-Analyzer-model-V2.4/BirdNET_GLOBAL_2.4_Model_FP32.tflite'

    # Create a mock S3 bucket
    s3 = boto3.client('s3')
    bucket_name = 'test-bucket'
    s3.create_bucket(Bucket=bucket_name)

    # Create a mock DynamoDB table
    dynamodb = boto3.resource('dynamodb')
    table = dynamodb.create_table(
        TableName='BirdTagMedia',
        KeySchema=[{'AttributeName': 'id', 'KeyType': 'HASH'}],
        AttributeDefinitions=[{'AttributeName': 'id', 'AttributeType': 'S'}],
        BillingMode='PAY_PER_REQUEST'
    )

    # Read the actual test audio file
    test_audio_path = './test_audio.wav'
    with open(test_audio_path, 'rb') as f:
        test_audio_content = f.read()

    # Upload the test audio file to S3
    test_key = 'upload/audio/test_audio.wav'
    s3.put_object(
        Bucket=bucket_name,
        Key=test_key,
        Body=test_audio_content,
        ContentType='audio/wav'
    )

    print(f"\nTesting with audio: {test_audio_path}")
    print(f"Audio size: {len(test_audio_content)} bytes")

    # Create a mock S3 event
    event = create_s3_event(bucket_name, test_key)

    # Call the lambda function
    print("\nCalling lambda_handler...")
    response = lambda_handler(event, {})

    # Validate the response
    assert response['statusCode'] == 200
    print("\nLambda response:", json.dumps(response, indent=2))

    # Validate the DynamoDB record
    table = dynamodb.Table('BirdTagMedia')
    items = table.scan()['Items']
    assert len(items) == 1
    item = items[0]
    print("\nDynamoDB record:", json.dumps(item, indent=2, default=str))


def run_manual_test():
    """Run BirdNET analyze and lambda_handler manually for local debugging."""
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
    # You can modify bucket/key as needed, or place a local test audio file
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
        function_name = "test_lambda"
        memory_limit_in_mb = 128
        invoked_function_arn = "arn:aws:lambda:us-east-1:123456789012:function:test_lambda"
        aws_request_id = "test-request-id"
    # Run lambda_handler
    response = lambda_handler(MOCK_EVENT, MockContext())
    print("Lambda Response:")
    print(json.dumps(json.loads(response["body"]), indent=2, ensure_ascii=False))
    # Check output format
    required_keys = ["message", "media_id", "detected_species", "detection_segments", "file_location", "created_at"]
    body = json.loads(response["body"])
    missing = [k for k in required_keys if k not in body]
    if missing:
        print(f"❌ Missing fields: {missing}")
    else:
        print("✅ Output format is correct!")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="BirdNET Lambda Test Runner")
    parser.add_argument('--mode', choices=['mock', 'manual'], default='mock',
                        help="Choose 'mock' for moto-based AWS test, 'manual' for local BirdNET/lambda_handler test.")
    args = parser.parse_args()
    if args.mode == 'mock':
        run_mock_test()
    else:
        run_manual_test() 
