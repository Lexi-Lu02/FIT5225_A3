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
import random
import shutil
import hashlib
import base64

# 配置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# 检查本地测试模式
is_local_test = os.environ.get("LOCAL_TEST") == "1" or os.environ.get("DDB_TABLE") == "test-table"

# 初始化AWS客户端 - 只在非本地测试模式下连接真实AWS服务
if not is_local_test:
    s3 = boto3.client('s3')
    dynamodb = boto3.resource('dynamodb')
    table = dynamodb.Table(os.environ['DDB_TABLE'])
else:
    # 本地测试模式下使用模拟客户端
    s3 = None
    dynamodb = None
    table = None
    logger.info("Running in LOCAL TEST mode - AWS services disabled")

# 全局变量存储模型
model = None

def get_model():
    """获取YOLO模型实例"""
    global model
    if model is None:
        try:
            # 修复模型路径 - Docker中模型在 /var/task/model/ 目录下
            model_paths = [
                '/var/task/model/model.pt',  # Docker中的正确路径
                '/var/task/model.pt',        # 备用路径
                'model/model.pt',            # 相对路径
                'model.pt'                   # 当前目录
            ]
            
            model_path = None
            for path in model_paths:
                if os.path.exists(path):
                    model_path = path
                    logger.info(f"Found model at: {model_path}")
                    break
            
            if not model_path:
                raise FileNotFoundError("Model file not found in any expected location")
            
            logger.info(f"Loading YOLO model from: {model_path}")
            model = YOLO(model_path)
            logger.info("✅ YOLO model loaded successfully!")
            return model
            
        except Exception as e:
            logger.error(f"Error loading model: {e}")
            logger.error(traceback.format_exc())
            # 不再返回None或模拟结果，直接抛出异常
            raise Exception(f"Failed to load YOLO model: {str(e)}")
    
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

def process_image(bucket, key):
    """处理图片并进行鸟类检测"""
    try:
        logger.info(f"🐦 Processing image: {key}")
        
        # 获取模型 - 如果失败会抛出异常
        model = get_model()
        
        # 只支持S3模式，不再支持LOCAL_TEST模拟
        local_file = f"/tmp/{os.path.basename(key)}"
        s3 = boto3.client('s3')
        s3.download_file(bucket, key, local_file)
        
        # 使用真实模型进行检测
        logger.info("🔍 Running YOLO detection...")
        results = model(local_file)
        
        # 处理真实检测结果
        detection_results = []
        
        for r in results:
            boxes = r.boxes
            if boxes is not None:
                for box in boxes:
                    # 获取边界框坐标
                    xyxy = box.xyxy[0].tolist()  # [x1, y1, x2, y2]
                    conf = float(box.conf[0])    # 置信度
                    cls = int(box.cls[0])        # 类别ID
                    
                    # 获取类别名称
                    class_name = model.names[cls] if cls < len(model.names) else f"class_{cls}"
                    
                    detection_results.append({
                        'species': class_name,
                        'confidence': round(conf, 3),
                        'bounding_box': [int(x) for x in xyxy],
                        'class_id': cls
                    })
        
        # 如果没有检测到任何对象
        if not detection_results:
            return {
                'statusCode': 200,
                'body': json.dumps({
                    'message': 'No birds detected in image',
                    'detection_results': {
                        'species': None,
                        'confidence': 0.0,
                        'bounding_boxes': [],
                        'detected_objects': 0
                    }
                })
            }
        
        # 选择置信度最高的检测结果
        best_detection = max(detection_results, key=lambda x: x['confidence'])
        
        # 格式化返回结果
        response_body = {
            'message': 'Success',
            'detection_results': {
                'species': best_detection['species'],
                'confidence': best_detection['confidence'],
                'bounding_boxes': [best_detection['bounding_box']],
                'detected_objects': len(detection_results)
            }
        }
        
        logger.info(f"✅ Detection completed: {best_detection['species']} (confidence: {best_detection['confidence']})")
        
        # 清理临时文件
        if os.path.exists(local_file):
            os.remove(local_file)
        
        return {
            'statusCode': 200,
            'body': json.dumps(response_body)
        }
        
    except Exception as e:
        logger.error(f"Error processing image: {e}")
        logger.error(traceback.format_exc())
        
        # 返回错误而不是模拟数据
        return {
            'statusCode': 500,
            'body': json.dumps({
                'error': f'Model detection failed: {str(e)}',
                'message': 'Real model detection is required but failed'
            })
        }

def lambda_handler(event, context):
    """主处理函数"""
    try:
        logger.info(f"🚀 收到事件: {event}")
        
        # 检查是否有直接传入的图片数据
        if 'image_data' in event:
            # 直接处理base64编码的图片数据
            filename = event.get('filename', 'uploaded_image.jpg')
            logger.info(f"🖼️ 处理base64图片数据: {filename}")
            
            # 解码base64图片数据
            image_data = base64.b64decode(event['image_data'])
            
            # 保存到临时文件
            local_file = f"/tmp/{filename}"
            with open(local_file, 'wb') as f:
                f.write(image_data)
            
            # 验证图片
            try:
                with Image.open(local_file) as img:
                    logger.info(f"📏 图片尺寸: {img.size}, 格式: {img.format}")
            except Exception as e:
                logger.error(f"❌ 图片验证失败: {e}")
                return {
                    'statusCode': 400,
                    'body': json.dumps({'error': f'Invalid image: {str(e)}'})
                }
            
            # 获取模型并进行检测
            model = get_model()
            
            # 运行检测
            results = model(local_file)
            
            # 处理检测结果
            detection_data = []
            for result in results:
                boxes = result.boxes
                if boxes is not None:
                    for box in boxes:
                        cls_id = int(box.cls[0])
                        confidence = float(box.conf[0])
                        xyxy = box.xyxy[0].tolist()
                        
                        species_name = model.names[cls_id]
                        detection_data.append({
                            'species': species_name,
                            'confidence': confidence,
                            'bounding_box': xyxy
                        })
            
            # 返回检测结果
            if detection_data:
                best_detection = max(detection_data, key=lambda x: x['confidence'])
                response_data = {
                    "message": "Success",
                    "detection_results": {
                        "species": best_detection['species'],
                        "confidence": best_detection['confidence'],
                        "bounding_boxes": [best_detection['bounding_box']],
                        "detected_objects": len(detection_data)
                    }
                }
            else:
                response_data = {
                    "message": "No birds detected",
                    "detection_results": {
                        "species": "None",
                        "confidence": 0.0,
                        "bounding_boxes": [],
                        "detected_objects": 0
                    }
                }
            
            logger.info(f"✅ 检测完成: {response_data}")
            return {
                'statusCode': 200,
                'body': json.dumps(response_data)
            }
        
        # 处理传统的S3事件格式（保持向后兼容）
        elif 'Records' in event:
            record = event['Records'][0]
            bucket = record['s3']['bucket']['name']
            key = record['s3']['object']['key']
            return process_image(bucket, key)
        
        else:
            logger.error("❌ 无效的事件格式")
            return {
                'statusCode': 400,
                'body': json.dumps({'error': 'Invalid event format'})
            }
        
    except Exception as e:
        logger.error(f"Error in lambda_handler: {e}")
        logger.error(f"Traceback: {traceback.format_exc()}")
        return {
            'statusCode': 500,
            'body': json.dumps({'error': str(e)})
        } 