
import boto3
import os
from PIL import Image
import io
import logging

# Initialise logs with S3 client
logger = logging.getLogger()
logger.setLevel(logging.INFO)

s3 = boto3.client('s3')

# environment variables
DEST_BUCKET = os.environ.get('S3_THUMBNAIL_BUCKET', 'birdtag-thumbs-dev')
THUMBNAIL_FOLDER = os.environ.get('THUMBNAIL_PREFIX', 'thumbnails')
THUMBNAIL_SIZE = 256

def lambda_handler(event, context):
    try:
        record = event['Records'][0]
        source_bucket = record['s3']['bucket']['name']
        object_key = record['s3']['object']['key']

        if not object_key.lower().endswith(('.jpg', '.jpeg', '.png')):
            logger.info(f"Not an image file: {object_key}")
            return {'statusCode': 200, 'body': 'Skipped non-image'}

        logger.info(f"Processing image: {object_key}")

        # Download original image
        original_img = s3.get_object(Bucket=source_bucket, Key=object_key)['Body'].read()
        img = Image.open(io.BytesIO(original_img))
        img.thumbnail((THUMBNAIL_SIZE, THUMBNAIL_SIZE))
        img = img.convert('RGB')  

        # Generate thumbnail file name and path
        filename = os.path.basename(object_key)
        thumb_key = f'{THUMBNAIL_FOLDER}/{filename}'

        # Save as JPEG to memory
        buffer = io.BytesIO()
        img.save(buffer, format='JPEG')
        buffer.seek(0)

        # Upload thumbnails to target bucket
        s3.put_object(
            Bucket=DEST_BUCKET,
            Key=thumb_key,
            Body=buffer,
            ContentType='image/jpeg'
        )

        logger.info(f"Thumbnail saved: s3://{DEST_BUCKET}/{thumb_key}")
        return {
            'statusCode': 200,
            'body': f"Thumbnail created: {thumb_key}"
        }

    except Exception as e:
        logger.error(f"Error creating thumbnail: {str(e)}")
        return {
            'statusCode': 500,
            'body': str(e)
        }
