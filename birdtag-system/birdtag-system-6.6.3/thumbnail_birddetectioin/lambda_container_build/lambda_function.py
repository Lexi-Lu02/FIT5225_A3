import json
import os
import tempfile
import boto3
import uuid
from datetime import datetime
import logging
import traceback
import decimal
from ultralytics import YOLO
import cv2
import numpy as np
from PIL import Image
import io

# 配置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# 初始化AWS客户端
s3 = boto3.client('s3')
dynamodb = boto3.resource('dynamodb')
table = dynamodb.Table(os.environ['DDB_TABLE'])

# 全局变量存储模型
model = None

def get_model():
    """获取YOLO模型实例"""
    global model
    if model is None:
        try:
            # 检查是否在本地测试模式
            is_local_test = os.environ.get("LOCAL_TEST") == "1"
            
            if is_local_test:
                # 本地测试模式：使用当前目录下的模型文件
                model_path = os.path.join(os.getcwd(), "model.pt")
                logger.info(f"Local test: Loading model from current directory: {model_path}")
            else:
                # Lambda环境：使用容器内的模型文件
                root = os.environ.get('LAMBDA_TASK_ROOT', '/var/task')
                model_path = os.environ.get('MODEL_PATH', 'model/model.pt')
                model_path = os.path.join(root, model_path)
                logger.info(f"Lambda environment: Loading model from: {model_path}")
            
            model = YOLO(model_path)
            logger.info("Model loaded successfully")
        except Exception as e:
            logger.error(f"Error loading model: {str(e)}")
            logger.error(traceback.format_exc())
            raise
    return model

def float_to_decimal(obj):
    """将float类型转换为Decimal类型"""
    if isinstance(obj, float):
        return decimal.Decimal(str(obj))
    elif isinstance(obj, list):
        return [float_to_decimal(i) for i in obj]
    elif isinstance(obj, dict):
        return {k: float_to_decimal(v) for k, v in obj.items()}
    else:
        return obj

def move_file_to_species_folder(bucket: str, source_key: str, species_name: str) -> str:
    """将文件移动到物种文件夹"""
    filename = os.path.basename(source_key)
    new_key = f"species/{species_name}/{filename}"
    
    # 执行S3操作
    s3.copy_object(
        Bucket=bucket,
        CopySource={'Bucket': bucket, 'Key': source_key},
        Key=new_key
    )
    logger.info(f"Copied file to: {new_key}")
    
    s3.delete_object(
        Bucket=bucket,
        Key=source_key
    )
    logger.info(f"Deleted original file: {source_key}")
    
    return new_key

def save_to_dynamodb(
    bucket: str,
    original_key: str,
    new_key: str,
    thumbnail_key: str,
    detection_boxes: list,
    detected_species: list,
    created_at: str,
    user_id: str = None
) -> str:
    """保存分析结果到DynamoDB"""
    media_id = str(uuid.uuid4())
    item = {
        'id': media_id,
        'user_id': user_id,
        'file_type': 'image',
        's3_path': new_key,
        'thumbnail_path': thumbnail_key,
        'detected_species': detected_species,
        'detection_boxes': detection_boxes,
        'created_at': created_at
    }
    # 转换所有float为Decimal
    item = float_to_decimal(item)
    
    # 在本地测试模式下也写入DynamoDB
    table.put_item(Item=item)
    logger.info(f"Saved analysis results to DynamoDB with ID: {media_id}")
    return media_id

def process_image(bucket: str, key: str) -> dict:
    """处理图片并返回结果"""
    try:
        # 下载图片到临时文件
        local_file = f"/tmp/{os.path.basename(key)}"
        is_local_test = os.environ.get("LOCAL_TEST") == "1" or bucket == "test-bucket"
        if is_local_test:
            import shutil
            shutil.copyfile(os.path.basename(key), local_file)
            logger.info(f"Local test: copied {os.path.basename(key)} to {local_file}")
        else:
            s3.download_file(bucket, key, local_file)
            logger.info(f"Downloaded file to: {local_file}")
        
        # 生成缩略图
        thumbnail_key = f"thumbnail/{os.path.basename(key)}"
        with Image.open(local_file) as img:
            # 计算缩略图尺寸
            max_size = 200
            ratio = min(max_size/img.width, max_size/img.height)
            new_size = (int(img.width * ratio), int(img.height * ratio))
            # 生成缩略图
            thumbnail = img.resize(new_size, Image.Resampling.LANCZOS)
            # 保存缩略图到内存
            thumbnail_buffer = io.BytesIO()
            thumbnail.save(thumbnail_buffer, format='JPEG', quality=75)
            thumbnail_buffer.seek(0)
            # 上传缩略图到S3
            s3.upload_fileobj(
                thumbnail_buffer,
                bucket,
                thumbnail_key,
                ExtraArgs={'ContentType': 'image/jpeg'}
            )
            logger.info(f"Thumbnail uploaded: s3://{bucket}/{thumbnail_key}")
        
        # 运行模型推理
        logger.info("Running in LOCAL TEST mode" if is_local_test else "Running in AWS Lambda mode")
        model = get_model()
        results = model(local_file)
        
        # 处理检测结果
        detection_boxes = []
        detected_species_set = set()
        
        for result in results:
            boxes = result.boxes
            for box in boxes:
                # 获取坐标和置信度
                x1, y1, x2, y2 = box.xyxy[0].tolist()
                confidence = float(box.conf[0])
                class_id = int(box.cls[0])
                class_name = result.names[class_id]
                
                # 归一化坐标
                img_height, img_width = result.orig_shape
                x1, x2 = x1/img_width, x2/img_width
                y1, y2 = y1/img_height, y2/img_height
                
                detection_boxes.append({
                    'species': class_name,
                    'code': class_name.lower().replace(' ', '_'),
                    'box': [x1, y1, x2, y2],
                    'confidence': confidence
                })
                detected_species_set.add(class_name)
        
        detected_species = list(detected_species_set)
        logger.info(f"Detected {len(detected_species)} species: {detected_species_set}")
        
        # 获取最高置信度的物种
        highest_confidence_species = None
        if detection_boxes:
            highest_confidence_box = max(detection_boxes, key=lambda x: x['confidence'])
            highest_confidence_species = highest_confidence_box['species']
        else:
            highest_confidence_species = 'unknown'
        
        # 移动文件到物种文件夹
        new_key = move_file_to_species_folder(bucket, key, highest_confidence_species)
        logger.info(f"Moved file to species folder: {new_key}")
        
        # 保存到DynamoDB
        created_at = datetime.utcnow().isoformat()
        media_id = save_to_dynamodb(
            bucket=bucket,
            original_key=key,
            new_key=new_key,
            thumbnail_key=thumbnail_key,
            detection_boxes=detection_boxes,
            detected_species=detected_species,
            created_at=created_at
        )
        
        # 清理临时文件
        os.remove(local_file)
        logger.info("Cleaned up temporary file")
        
        return {
            'statusCode': 200,
            'body': json.dumps({
                'message': 'Image processed successfully',
                'record_id': media_id,
                'detected_species': detected_species,
                'detection_boxes': detection_boxes,
                'file_location': {
                    'original': key,
                    'new': new_key,
                    'thumbnail': thumbnail_key,
                    'species': highest_confidence_species
                },
                'created_at': created_at
            })
        }
        
    except Exception as e:
        logger.error(f"Error processing image: {str(e)}")
        logger.error(traceback.format_exc())
        return {
            'statusCode': 500,
            'body': json.dumps({
                'message': 'Error processing image',
                'error': str(e)
            })
        }

def lambda_handler(event, context):
    """Lambda函数入口点"""
    try:
        # 解析S3事件
        record = event['Records'][0]
        bucket = record['s3']['bucket']['name']
        key = record['s3']['object']['key']
        
        logger.info(f"Processing image: s3://{bucket}/{key}")
        return process_image(bucket, key)
        
    except Exception as e:
        logger.error(f"Error in lambda_handler: {str(e)}")
        logger.error(traceback.format_exc())
        return {
            'statusCode': 500,
            'body': json.dumps({
                'message': 'Internal server error',
                'error': str(e)
            })
        } 