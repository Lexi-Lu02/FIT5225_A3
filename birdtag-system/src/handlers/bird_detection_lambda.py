import json
import boto3
import cv2
import numpy as np
from ultralytics import YOLO
import supervision as sv
import os
import tempfile
import time
import logging

# 配置日志
logger = logging.getLogger()
logger.setLevel(logging.INFO)

# 初始化AWS客户端
s3_client = boto3.client('s3')
dynamodb = boto3.resource('dynamodb')

# 环境变量
MODEL_BUCKET = os.environ.get('MODEL_BUCKET')
MODEL_KEY = os.environ.get('MODEL_KEY', 'model.pt')
MEDIA_BUCKET = os.environ.get('MEDIA_BUCKET')
DYNAMODB_TABLE = os.environ.get('DYNAMODB_TABLE')

def get_cors_headers():
    """返回CORS头信息"""
    return {
        'Access-Control-Allow-Origin': '*',
        'Access-Control-Allow-Headers': 'Content-Type,X-Amz-Date,Authorization,X-Api-Key,X-Amz-Security-Token',
        'Access-Control-Allow-Methods': 'GET,POST,PUT,DELETE,OPTIONS'
    }

def process_image(image_path, model_path, confidence=0.5):
    """
    处理单张图片并返回检测结果
    
    Args:
        image_path (str): 图片路径
        model_path (str): 模型路径
        confidence (float): 置信度阈值
    
    Returns:
        tuple: (检测结果列表, 标注后的图片)
    """
    try:
        # 加载模型
        model = YOLO(model_path)
        
        # 读取图片
        img = cv2.imread(image_path)
        if img is None:
            raise Exception("Failed to read image")
        
        # 运行检测
        result = model(img)[0]
        detections = sv.Detections.from_ultralytics(result)
        
        # 提取检测结果
        detection_results = []
        if detections.class_id is not None:
            detections = detections[(detections.confidence > confidence)]
            for cls_id, conf in zip(detections.class_id, detections.confidence):
                detection_results.append({
                    'species': model.names[cls_id],
                    'confidence': float(conf)
                })
        
        # 创建标注图片
        annotated_img = img.copy()
        if len(detection_results) > 0:
            box_annotator = sv.BoxAnnotator()
            label_annotator = sv.LabelAnnotator()
            
            box_annotator.annotate(annotated_img, detections=detections)
            labels = [f"{r['species']} {r['confidence']*100:.2f}%" for r in detection_results]
            label_annotator.annotate(annotated_img, detections=detections, labels=labels)
        
        return detection_results, annotated_img
        
    except Exception as e:
        logger.error(f"Error in process_image: {str(e)}")
        raise

def lambda_handler(event, context):
    """
    Lambda处理函数
    
    Args:
        event (dict): Lambda事件
        context (object): Lambda上下文
    
    Returns:
        dict: 处理结果
    """
    try:
        logger.info(f"Received event: {json.dumps(event)}")
        
        # 检查是否是S3触发事件
        if 'Records' in event and event['Records'][0]['eventSource'] == 'aws:s3':
            bucket = event['Records'][0]['s3']['bucket']['name']
            key = event['Records'][0]['s3']['object']['key']
        else:
            # 处理API Gateway请求
            body = json.loads(event.get('body', '{}'))
            bucket = body.get('bucket')
            key = body.get('key')
            
            if not bucket or not key:
                return {
                    'statusCode': 400,
                    'headers': get_cors_headers(),
                    'body': json.dumps({'error': 'Missing bucket or key parameter'})
                }
        
        # 下载图片到临时文件
        with tempfile.NamedTemporaryFile(suffix='.jpg') as tmp_file:
            s3_client.download_file(bucket, key, tmp_file.name)
            
            # 下载模型文件
            model_path = '/tmp/model.pt'
            if not os.path.exists(model_path):
                s3_client.download_file(MODEL_BUCKET, MODEL_KEY, model_path)
            
            # 处理图片
            detection_results, annotated_img = process_image(tmp_file.name, model_path)
            
            # 保存结果图片
            result_key = f"results/{os.path.basename(key)}"
            with tempfile.NamedTemporaryFile(suffix='.jpg') as result_file:
                cv2.imwrite(result_file.name, annotated_img)
                s3_client.upload_file(result_file.name, MEDIA_BUCKET, result_key)
            
            # 保存结果到DynamoDB
            table = dynamodb.Table(DYNAMODB_TABLE)
            table.put_item(Item={
                'fileKey': key,
                'type': 'image',
                'detectionResults': detection_results,
                'resultImageKey': result_key,
                'timestamp': int(time.time())
            })
            
            return {
                'statusCode': 200,
                'headers': get_cors_headers(),
                'body': json.dumps({
                    'message': 'Processing completed',
                    'detections': detection_results,
                    'resultImageKey': result_key
                })
            }
            
    except Exception as e:
        logger.error(f"Error in lambda_handler: {str(e)}")
        return {
            'statusCode': 500,
            'headers': get_cors_headers(),
            'body': json.dumps({'error': str(e)})
        } 