import json
import os
import boto3
import moto
from moto import mock_aws
import pytest
import uuid
from datetime import datetime
import logging
import traceback
from decimal import Decimal

# Configure logging for test execution
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Custom JSON encoder to handle Decimal type serialization
class DecimalEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, Decimal):
            return float(obj)
        return super(DecimalEncoder, self).default(obj)

# Set environment variables (before importing lambda_function)
os.environ['LOCAL_TEST'] = '1'
os.environ['DDB_TABLE'] = 'BirdTagMedia'
os.environ['AWS_DEFAULT_REGION'] = 'us-east-1'  # Set default AWS region

# Import lambda_function after environment setup
from lambda_function import lambda_handler, float_to_decimal

# Helper function to create S3 event payload
def create_s3_event(bucket, key):
    return {
        'Records': [{
            's3': {
                'bucket': {'name': bucket},
                'object': {'key': key}
            }
        }]
    }

@mock_aws
def test_lambda_function():
    """
    Comprehensive test suite for lambda_function.
    Tests the complete pipeline including:
    - S3 event handling
    - Image processing
    - Model inference
    - DynamoDB persistence
    - File organization
    """
    try:
        logger.info("Starting lambda function test...")
        logger.info("Environment variables:")
        logger.info(f"LOCAL_TEST: {os.environ.get('LOCAL_TEST')}")
        logger.info(f"DDB_TABLE: {os.environ.get('DDB_TABLE')}")
        logger.info(f"AWS_DEFAULT_REGION: {os.environ.get('AWS_DEFAULT_REGION')}")
        
        # Initialize mock S3 bucket
        s3 = boto3.client('s3', region_name='us-east-1')
        bucket_name = 'test-bucket'
        try:
            # No LocationConstraint needed for us-east-1
            s3.create_bucket(Bucket=bucket_name)
            logger.info(f"Created mock S3 bucket: {bucket_name}")
        except Exception as e:
            # Continue if bucket already exists
            if 'BucketAlreadyOwnedByYou' in str(e):
                logger.info(f"Bucket {bucket_name} already exists, continuing...")
            else:
                raise
        
        # Initialize mock DynamoDB table
        dynamodb = boto3.resource('dynamodb', region_name='us-east-1')
        table = dynamodb.create_table(
            TableName='BirdTagMedia',
            KeySchema=[{'AttributeName': 'id', 'KeyType': 'HASH'}],
            AttributeDefinitions=[{'AttributeName': 'id', 'AttributeType': 'S'}],
            BillingMode='PAY_PER_REQUEST'
        )
        logger.info("Created mock DynamoDB table")
        
        # Load test image for processing
        test_image_path = './test_image.jpg'
        if not os.path.exists(test_image_path):
            raise FileNotFoundError(f"Test image not found: {test_image_path}")
            
        with open(test_image_path, 'rb') as f:
            test_image_content = f.read()
        logger.info(f"Loaded test image: {test_image_path} ({len(test_image_content)} bytes)")
        
        # Upload test image to mock S3
        test_key = 'upload/image/test_image.jpg'
        s3.put_object(
            Bucket=bucket_name,
            Key=test_key,
            Body=test_image_content,
            ContentType='image/jpeg'
        )
        logger.info(f"Uploaded test image to S3: {test_key}")
        
        # Create S3 event trigger
        event = create_s3_event(bucket_name, test_key)
        logger.info("Created S3 event")
        
        # Execute lambda function
        logger.info("Calling lambda_handler...")
        response = lambda_handler(event, {})
        
        # Validate response status
        assert response['statusCode'] == 200, f"Expected status code 200, got {response['statusCode']}"
        logger.info(f"Lambda response: {json.dumps(response, indent=2)}")
        
        # Parse response payload
        response_body = json.loads(response['body'])
        media_id = response_body['record_id']
        
        # Verify DynamoDB record creation
        table = dynamodb.Table('BirdTagMedia')
        items = table.scan()['Items']
        assert len(items) == 1, f"Expected 1 item in DynamoDB, got {len(items)}"
        
        item = items[0]
        # Serialize DynamoDB record using custom encoder
        logger.info(f"DynamoDB record: {json.dumps(item, indent=2, cls=DecimalEncoder)}")
        
        # Validate required fields in DynamoDB record
        required_fields = ['id', 'file_type', 'detected_species', 'detection_boxes', 
                         'thumbnail_path', 's3_path', 'created_at']
        for field in required_fields:
            assert field in item, f"Missing required field: {field}"
        assert item['file_type'] == 'image', f"Expected file_type 'image', got {item['file_type']}"
        assert item['id'] == media_id, f"Expected media_id {media_id}, got {item['id']}"
        
        # Log detection results
        logger.info("\nDetection Results:")
        logger.info(f"Detected species: {item['detected_species']}")
        logger.info(f"Number of detections: {len(item['detection_boxes'])}")
        for i, box in enumerate(item['detection_boxes']):
            logger.info(f"\nDetection {i+1}:")
            logger.info(f"  Species: {box['species']}")
            logger.info(f"  Confidence: {float(box['confidence']):.4f}")
            logger.info(f"  Box: {[float(x) for x in box['box']]}")
        
        # Verify S3 file relocation
        try:
            s3.head_object(Bucket=bucket_name, Key=test_key)
            raise AssertionError("Original file should be moved")
        except:
            logger.info("✓ Original file moved successfully")
        
        # Verify thumbnail generation
        thumbnail_key = item['thumbnail_path']
        try:
            s3.head_object(Bucket=bucket_name, Key=thumbnail_key)
            logger.info("✓ Thumbnail generated successfully")
        except:
            raise AssertionError("Thumbnail should exist")
        
        # Verify species directory organization
        species_key = item['s3_path']
        try:
            s3.head_object(Bucket=bucket_name, Key=species_key)
            logger.info("✓ File moved to species directory successfully")
        except:
            raise AssertionError("File should be moved to species directory")
            
        logger.info("\nAll tests passed! ✓")
        return True
        
    except Exception as e:
        logger.error(f"Test failed with error: {str(e)}")
        logger.error("Traceback:")
        logger.error(traceback.format_exc())
        raise

if __name__ == "__main__":
    try:
        test_lambda_function()
    except Exception as e:
        logger.error(f"Test execution failed: {str(e)}")
        exit(1) 
