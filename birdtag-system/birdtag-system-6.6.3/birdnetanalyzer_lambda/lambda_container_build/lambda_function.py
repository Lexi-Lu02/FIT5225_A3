import json
import os
import tempfile
import boto3
import uuid
from datetime import datetime
import numpy as np
from aws_lambda_powertools import Logger
from aws_lambda_powertools.utilities.typing import LambdaContext
from aws_lambda_powertools.utilities.data_classes import S3Event
from birdnet_analyzer.analyze import analyze
import traceback
import decimal

# Initialize logger
logger = Logger()

# Initialize AWS clients
s3 = boto3.client('s3')
dynamodb = boto3.resource('dynamodb')
table = dynamodb.Table(os.environ['DDB_TABLE'])

# Set environment variables for BirdNET-Analyzer
os.environ["NUMBA_CACHE_DIR"] = "/tmp/numba_cache"
import birdnet_analyzer.config as cfg
cfg.ERROR_LOG_FILE = "/tmp/error_log.txt"

def move_file_to_species_folder(bucket: str, source_key: str, species_name: str) -> str:
    """
    Move file to species folder in S3
    Returns the new key of the file
    """
    is_local_test = os.environ.get("LOCAL_TEST") == "1" or bucket == "test-bucket"
    filename = os.path.basename(source_key)
    new_key = f"species/{species_name}/{filename}"
    if is_local_test:
        logger.info(f"Local test: skip S3 copy_object and delete_object, return {new_key}")
        return new_key
    # 云端环境才做S3操作
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

def float_to_decimal(obj):
    if isinstance(obj, float):
        return decimal.Decimal(str(obj))
    elif isinstance(obj, list):
        return [float_to_decimal(i) for i in obj]
    elif isinstance(obj, dict):
        return {k: float_to_decimal(v) for k, v in obj.items()}
    else:
        return obj

def save_to_dynamodb(
    bucket: str,
    original_key: str,
    new_key: str,
    species_summary: dict,
    created_at: str,
    detection_segments: list,
    detected_species: list,
    user_id: str = None
) -> str:
    """
    Save analysis results to DynamoDB
    """
    is_local_test = os.environ.get("LOCAL_TEST") == "1" or os.environ.get("DDB_TABLE") == "your-dynamodb-table-name"
    media_id = str(uuid.uuid4())
    item = {
        'id': media_id,
        'user_id': user_id,
        'file_type': 'audio',
        's3_path': new_key,
        'thumbnail_path': None,
        'detected_species': detected_species,
        'detection_segments': detection_segments,
        'created_at': created_at
    }
    item = float_to_decimal(item)
    if is_local_test:
        logger.info(f"Local test: skip DynamoDB put_item, would save: {item}")
        return media_id
    table.put_item(Item=item)
    logger.info(f"Saved analysis results to DynamoDB with ID: {media_id}")
    return media_id

@logger.inject_lambda_context
def lambda_handler(event: dict, context: LambdaContext) -> dict:
    """
    Lambda function handler for BirdNET audio analysis
    """
    try:
        # 兼容本地测试和Lambda环境的S3事件解析
        try:
            s3_event = S3Event(event)
            records = list(s3_event.records)
            record = records[0]
            bucket = record.s3.bucket.name
            key = record.s3.get_object.key
        except Exception:
            record = event["Records"][0]
            bucket = record["s3"]["bucket"]["name"]
            key = record["s3"]["object"]["key"]
        
        logger.info(f"Processing audio file: {key} from bucket: {bucket}")
        
        # Validate file extension
        if not key.lower().endswith(('.wav', '.mp3', '.flac')):
            raise ValueError(f"Unsupported file format: {key}")
        
        # 本地测试时跳过S3下载，直接用本地文件
        local_file = f"/tmp/{os.path.basename(key)}"
        is_local_test = os.environ.get("LOCAL_TEST") == "1" or bucket == "test-bucket"
        if is_local_test:
            import shutil
            shutil.copyfile(os.path.basename(key), local_file)
            logger.info(f"Local test: copied {os.path.basename(key)} to {local_file}")
        else:
            s3.download_file(bucket, key, local_file)
            logger.info(f"Downloaded file to: {local_file}")
        
        # 直接调用BirdNET-Analyzer的analyze进行音频分析
        output_dir = "/tmp/birdnet_output"
        os.makedirs(output_dir, exist_ok=True)
        analyze(
            input=local_file,
            output=output_dir,
            min_conf=0.1,
            sensitivity=1.0,
            overlap=0.0,
            threads=1,
            batch_size=1,
            lat=None,
            lon=None,
            week=None
        )
        # 查找输出结果文件（.BirdNET.selection.table.txt）
        base_name = os.path.splitext(os.path.basename(local_file))[0]
        result_file = os.path.join(output_dir, f"{base_name}.BirdNET.selection.table.txt")
        predictions = []
        if os.path.exists(result_file):
            with open(result_file, "r", encoding="utf-8") as f:
                lines = f.readlines()
                header = None
                for line in lines:
                    if line.startswith("Selection"):
                        header = [h.strip() for h in line.strip().split("\t")]
                        continue
                    if header and line.strip() and not line.startswith("Selection"):
                        values = line.strip().split("\t")
                        pred = dict(zip(header, values))
                        predictions.append(pred)
        predictions = list(predictions)
        logger.info(f"Found {len(predictions)} bird detections")
        
        # 构建 detection_segments 和 detected_species
        detection_segments = []
        detected_species_set = set()
        for pred in predictions:
            try:
                detection_segments.append({
                    'species': pred['Common Name'],
                    'code': pred.get('Species Code', ''),
                    'start': float(pred['Begin Time (s)']),
                    'end': float(pred['End Time (s)']),
                    'confidence': float(pred['Confidence'])
                })
                detected_species_set.add(pred['Common Name'])
            except Exception as e:
                logger.error(f"Error parsing prediction row: {pred}, error: {e}")
        detected_species = list(detected_species_set)
        
        # 物种统计
        species_summary = {}
        for seg in detection_segments:
            species = seg['species']
            if species not in species_summary:
                species_summary[species] = {
                    'count': 0,
                    'max_confidence': 0
                }
            species_summary[species]['count'] += 1
            species_summary[species]['max_confidence'] = max(
                species_summary[species]['max_confidence'],
                seg['confidence']
            )
        # 取最高置信度物种
        highest_confidence_species = None
        if species_summary:
            highest_confidence_species = max(
                list(species_summary.items()),
                key=lambda x: x[1]['max_confidence']
            )[0]
        else:
            highest_confidence_species = 'unknown'
        
        # Move file to species folder
        new_key = move_file_to_species_folder(bucket, key, highest_confidence_species)
        logger.info(f"Moved file to species folder: {new_key}")
        
        # Save to DynamoDB
        created_at = datetime.utcnow().isoformat()
        user_id = event.get('user_id') or None
        media_id = save_to_dynamodb(
            bucket=bucket,
            original_key=key,
            new_key=new_key,
            species_summary=species_summary,
            created_at=created_at,
            detection_segments=detection_segments,
            detected_species=detected_species,
            user_id=user_id
        )
        
        # Clean up temporary file
        os.remove(local_file)
        logger.info("Cleaned up temporary file")
        
        return {
            'statusCode': 200,
            'body': json.dumps({
                'message': 'Success',
                'media_id': media_id,
                'detected_species': detected_species,
                'detection_segments': detection_segments,
                'file_location': {
                    'original': key,
                    'new': new_key,
                    'species': highest_confidence_species
                },
                'created_at': created_at
            })
        }
        
    except ValueError as ve:
        logger.error(f"Validation error: {str(ve)}")
        return {
            'statusCode': 400,
            'body': json.dumps({
                'message': 'Bad Request',
                'error': str(ve)
            })
        }
    except Exception as e:
        logger.error(f"Error processing file: {str(e)}\n{traceback.format_exc()}")
        return {
            'statusCode': 500,
            'body': json.dumps({
                'message': 'Internal Server Error',
                'error': f"{str(e)}\n{traceback.format_exc()}"
            })
        } 
