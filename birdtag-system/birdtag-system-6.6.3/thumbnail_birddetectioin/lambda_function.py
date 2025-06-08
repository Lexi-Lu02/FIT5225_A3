import json
import os
import boto3
from PIL import Image
import io
import uuid
import base64
from datetime import datetime

s3_client = boto3.client('s3')

def lambda_handler(event, context):
    """
    Lambda function to generate thumbnails for uploaded images and classify them.
    Triggered by S3 ObjectCreated events.
    """
    try:
        # Get the bucket and key from the S3 event
        bucket = event['Records'][0]['s3']['bucket']['name']
        key = event['Records'][0]['s3']['object']['key']
        
        # Only process files in the upload/image/ directory
        if not key.startswith('upload/image/'):
            return {
                'statusCode': 200,
                'body': json.dumps('Not an image file, skipping thumbnail generation')
            }
            
        # Download the image from S3
        response = s3_client.get_object(Bucket=bucket, Key=key)
        image_content = response['Body'].read()
        
        # Open the image using PIL
        image = Image.open(io.BytesIO(image_content))
        
        # Calculate new dimensions while maintaining aspect ratio
        max_size = 200
        ratio = min(max_size/image.size[0], max_size/image.size[1])
        new_size = tuple(int(dim * ratio) for dim in image.size)
        
        # Create thumbnail
        image.thumbnail(new_size, Image.Resampling.LANCZOS)
        
        # Convert to JPEG and save to bytes
        output = io.BytesIO()
        image.convert('RGB').save(output, format='JPEG', quality=75)
        output.seek(0)
        
        # Generate thumbnail key
        filename = os.path.basename(key)
        thumbnail_key = f'thumbnail/{filename}'
        
        # Upload thumbnail to S3
        s3_client.upload_fileobj(
            output,
            bucket,
            thumbnail_key,
            ExtraArgs={'ContentType': 'image/jpeg'}
        )
        
        # =====================
        # 2nd lambda function
        # =====================
        # ========== 分类推理和写入数据库 ==========
        try:
            # 转 base64
            image_for_classify = Image.open(io.BytesIO(image_content))
            buffered = io.BytesIO()
            image_for_classify.save(buffered, format="JPEG")
            img_str = base64.b64encode(buffered.getvalue()).decode()

            sagemaker = boto3.client('sagemaker-runtime')
            sm_response = sagemaker.invoke_endpoint(
                EndpointName=os.environ['SAGEMAKER_ENDPOINT'],
                ContentType='application/json',
                Body=json.dumps({'image': img_str})
            )
            result = json.loads(sm_response['Body'].read())

            # 兼容 inference.py 输出格式
            if 'body' in result:
                result_body = json.loads(result['body'])
                labels = result_body.get('labels', [])
                probs = result_body.get('probs', [])
            else:
                labels = result.get('labels', [])
                probs = result.get('probs', [])

            # 取置信度最高的标签
            if labels and probs:
                max_prob_idx = probs.index(max(probs))
                species = labels[max_prob_idx]
                confidence = probs[max_prob_idx]
            else:
                species = 'unknown'
                confidence = 0.0

            # 生成唯一ID
            media_id = str(uuid.uuid4())

            # 写入 DynamoDB
            dynamodb = boto3.resource('dynamodb')
            item = {
                'id': media_id,
                's3_url': f's3://{bucket}/{key}',
                'thumbnail_url': f's3://{bucket}/thumbnail/{os.path.basename(key)}',
                'media_type': 'image',
                'tags': labels,
                'created_at': datetime.utcnow().isoformat(),
                'species': species,
                'confidence': confidence
            }
            table = dynamodb.Table(os.environ['DDB_TABLE'])
            table.put_item(Item=item)

            # 移动文件到 species 目录
            new_key = f'species/{species}/{os.path.basename(key)}'
            s3_client.copy_object(
                Bucket=bucket,
                CopySource={'Bucket': bucket, 'Key': key},
                Key=new_key
            )
            s3_client.delete_object(Bucket=bucket, Key=key)

        except Exception as e:
            print(f"Error in classification: {str(e)}")
        
        return {
            'statusCode': 200,
            'body': json.dumps({
                'message': 'Thumbnail and classification completed',
                'thumbnail_key': thumbnail_key,
                'species': species if 'species' in locals() else None,
                'confidence': confidence if 'confidence' in locals() else None
            })
        }
        
    except Exception as e:
        print(f'Error generating thumbnail: {str(e)}')
        return {
            'statusCode': 500,
            'body': json.dumps({
                'error': str(e)
            })
        } 