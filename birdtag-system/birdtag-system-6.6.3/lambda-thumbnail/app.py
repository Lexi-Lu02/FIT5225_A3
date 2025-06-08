import json
import os
import boto3
from PIL import Image
import io

s3_client = boto3.client('s3')

def lambda_handler(event, context):
    bucket = event['Records'][0]['s3']['bucket']['name']
    key    = event['Records'][0]['s3']['object']['key']

    if not key.startswith('upload/image/'):
        return {'statusCode':200,'body':json.dumps('skip')}

    resp = s3_client.get_object(Bucket=bucket, Key=key)
    img_bytes = resp['Body'].read()
    img = Image.open(io.BytesIO(img_bytes))

    # 按最长边 200px 缩放
    max_size = 200
    ratio = min(max_size/img.width, max_size/img.height)
    new_size = (int(img.width*ratio), int(img.height*ratio))
    img.thumbnail(new_size, Image.Resampling.LANCZOS)

    buf = io.BytesIO()
    img.convert('RGB').save(buf, format='JPEG', quality=75)
    buf.seek(0)

    thumb_key = 'thumbnail/' + os.path.basename(key)
    s3_client.upload_fileobj(buf, bucket, thumb_key,
        ExtraArgs={'ContentType':'image/jpeg'})

    return {'statusCode':200,'body':json.dumps({'thumbnail':thumb_key})}
