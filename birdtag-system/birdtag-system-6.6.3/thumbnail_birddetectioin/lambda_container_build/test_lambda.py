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

# 配置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# 自定义JSON编码器处理Decimal类型
class DecimalEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, Decimal):
            return float(obj)
        return super(DecimalEncoder, self).default(obj)

# 设置环境变量（在导入lambda_function之前）
os.environ['LOCAL_TEST'] = '1'
os.environ['DDB_TABLE'] = 'BirdTagMedia'
os.environ['AWS_DEFAULT_REGION'] = 'us-east-1'  # 设置默认区域

# 现在导入lambda_function
from lambda_function import lambda_handler, float_to_decimal

# 测试用的S3事件
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
    """测试完整的lambda_function功能"""
    try:
        logger.info("Starting lambda function test...")
        logger.info("Environment variables:")
        logger.info(f"LOCAL_TEST: {os.environ.get('LOCAL_TEST')}")
        logger.info(f"DDB_TABLE: {os.environ.get('DDB_TABLE')}")
        logger.info(f"AWS_DEFAULT_REGION: {os.environ.get('AWS_DEFAULT_REGION')}")
        
        # 创建mock S3 bucket
        s3 = boto3.client('s3', region_name='us-east-1')
        bucket_name = 'test-bucket'
        try:
            # us-east-1 不需要指定 LocationConstraint
            s3.create_bucket(Bucket=bucket_name)
            logger.info(f"Created mock S3 bucket: {bucket_name}")
        except Exception as e:
            # 如果bucket已存在，继续测试
            if 'BucketAlreadyOwnedByYou' in str(e):
                logger.info(f"Bucket {bucket_name} already exists, continuing...")
            else:
                raise
        
        # 创建mock DynamoDB表
        dynamodb = boto3.resource('dynamodb', region_name='us-east-1')
        table = dynamodb.create_table(
            TableName='BirdTagMedia',
            KeySchema=[{'AttributeName': 'id', 'KeyType': 'HASH'}],
            AttributeDefinitions=[{'AttributeName': 'id', 'AttributeType': 'S'}],
            BillingMode='PAY_PER_REQUEST'
        )
        logger.info("Created mock DynamoDB table")
        
        # 读取实际的测试图片
        test_image_path = './test_image.jpg'
        if not os.path.exists(test_image_path):
            raise FileNotFoundError(f"Test image not found: {test_image_path}")
            
        with open(test_image_path, 'rb') as f:
            test_image_content = f.read()
        logger.info(f"Loaded test image: {test_image_path} ({len(test_image_content)} bytes)")
        
        # 上传测试图片到S3
        test_key = 'upload/image/test_image.jpg'
        s3.put_object(
            Bucket=bucket_name,
            Key=test_key,
            Body=test_image_content,
            ContentType='image/jpeg'
        )
        logger.info(f"Uploaded test image to S3: {test_key}")
        
        # 创建S3事件
        event = create_s3_event(bucket_name, test_key)
        logger.info("Created S3 event")
        
        # 调用lambda函数
        logger.info("Calling lambda_handler...")
        response = lambda_handler(event, {})
        
        # 验证响应
        assert response['statusCode'] == 200, f"Expected status code 200, got {response['statusCode']}"
        logger.info(f"Lambda response: {json.dumps(response, indent=2)}")
        
        # 解析响应体
        response_body = json.loads(response['body'])
        media_id = response_body['record_id']
        
        # 验证DynamoDB记录
        table = dynamodb.Table('BirdTagMedia')
        items = table.scan()['Items']
        assert len(items) == 1, f"Expected 1 item in DynamoDB, got {len(items)}"
        
        item = items[0]
        # 使用自定义编码器序列化DynamoDB记录
        logger.info(f"DynamoDB record: {json.dumps(item, indent=2, cls=DecimalEncoder)}")
        
        # 验证所有必需字段
        required_fields = ['id', 'file_type', 'detected_species', 'detection_boxes', 
                         'thumbnail_path', 's3_path', 'created_at']
        for field in required_fields:
            assert field in item, f"Missing required field: {field}"
        assert item['file_type'] == 'image', f"Expected file_type 'image', got {item['file_type']}"
        assert item['id'] == media_id, f"Expected media_id {media_id}, got {item['id']}"
        
        # 打印检测结果
        logger.info("\nDetection Results:")
        logger.info(f"Detected species: {item['detected_species']}")
        logger.info(f"Number of detections: {len(item['detection_boxes'])}")
        for i, box in enumerate(item['detection_boxes']):
            logger.info(f"\nDetection {i+1}:")
            logger.info(f"  Species: {box['species']}")
            logger.info(f"  Confidence: {float(box['confidence']):.4f}")
            logger.info(f"  Box: {[float(x) for x in box['box']]}")
        
        # 验证S3文件移动
        try:
            s3.head_object(Bucket=bucket_name, Key=test_key)
            raise AssertionError("Original file should be moved")
        except:
            logger.info("✓ Original file moved successfully")
        
        # 验证缩略图生成
        thumbnail_key = item['thumbnail_path']
        try:
            s3.head_object(Bucket=bucket_name, Key=thumbnail_key)
            logger.info("✓ Thumbnail generated successfully")
        except:
            raise AssertionError("Thumbnail should exist")
        
        # 验证文件移动到species目录
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