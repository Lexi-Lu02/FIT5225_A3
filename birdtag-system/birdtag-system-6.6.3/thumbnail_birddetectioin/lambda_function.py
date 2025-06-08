import json
import os
import boto3
from PIL import Image
import io
import uuid
import base64
from datetime import datetime

# Initialize the S3 client
s3_client = boto3.client('s3')

def lambda_handler(event, context):
    """
    AWS Lambda entry point.
    Triggered by S3 ObjectCreated events.
    Generates a thumbnail for the uploaded image,
    invokes a SageMaker endpoint for classification,
    writes results to DynamoDB, and moves the original file.
    """
    try:
        # Extract bucket name and object key from the S3 event
        bucket = event['Records'][0]['s3']['bucket']['name']
        key = event['Records'][0]['s3']['object']['key']
        
        # Only handle objects in the upload/image/ prefix
        if not key.startswith('upload/image/'):
            return {
                'statusCode': 200,
                'body': json.dumps('Not an image file; skipping thumbnail generation.')
            }
        
        # Download the image bytes from S3
        response = s3_client.get_object(Bucket=bucket, Key=key)
        image_content = response['Body'].read()
        
        # Load image into PIL
        image = Image.open(io.BytesIO(image_content))
        
        # Determine thumbnail size (max 200px on longest side) while preserving aspect ratio
        max_size = 200
        ratio = min(max_size / image.width, max_size / image.height)
        new_size = (int(image.width * ratio), int(image.height * ratio))
        
        # Generate the thumbnail using high-quality resampling
        image.thumbnail(new_size, Image.Resampling.LANCZOS)
        
        # Convert thumbnail to JPEG and write to an in-memory buffer
        output = io.BytesIO()
        image.convert('RGB').save(output, format='JPEG', quality=75)
        output.seek(0)
        
        # Construct the S3 key for the thumbnail
        filename = os.path.basename(key)
        thumbnail_key = f'thumbnail/{filename}'
        
        # Upload the thumbnail back to S3 with appropriate content type
        s3_client.upload_fileobj(
            output,
            bucket,
            thumbnail_key,
            ExtraArgs={'ContentType': 'image/jpeg'}
        )
        
        # ---------------------------------------------------------------------
        # Classification step: invoke SageMaker and write metadata to DynamoDB
        # ---------------------------------------------------------------------
        try:
            # Prepare the original image as a base64-encoded JPEG payload
            buffered = io.BytesIO()
            Image.open(io.BytesIO(image_content)).save(buffered, format='JPEG')
            img_str = base64.b64encode(buffered.getvalue()).decode()
            
            # Invoke the SageMaker endpoint
            sagemaker = boto3.client('sagemaker-runtime')
            sm_response = sagemaker.invoke_endpoint(
                EndpointName=os.environ['SAGEMAKER_ENDPOINT'],
                ContentType='application/json',
                Body=json.dumps({'image': img_str})
            )
            result = json.loads(sm_response['Body'].read())
            
            # Unpack labels and probabilities (handle two possible response formats)
            if 'body' in result:
                body = json.loads(result['body'])
                labels = body.get('labels', [])
                probs = body.get('probs', [])
            else:
                labels = result.get('labels', [])
                probs = result.get('probs', [])
            
            # Choose the label with the highest probability
            if labels and probs:
                idx = probs.index(max(probs))
                species = labels[idx]
                confidence = probs[idx]
            else:
                species = 'unknown'
                confidence = 0.0
            
            # Generate a unique ID for this media item
            media_id = str(uuid.uuid4())
            
            # Assemble the item to store in DynamoDB
            dynamodb = boto3.resource('dynamodb')
            table = dynamodb.Table(os.environ['DDB_TABLE'])
            item = {
                'id': media_id,
                's3_url': f's3://{bucket}/{key}',
                'thumbnail_url': f's3://{bucket}/{thumbnail_key}',
                'media_type': 'image',
                'tags': labels,
                'created_at': datetime.utcnow().isoformat(),
                'species': species,
                'confidence': confidence
            }
            table.put_item(Item=item)
            
            # Move the original file into a species-specific folder
            new_key = f'species/{species}/{filename}'
            s3_client.copy_object(
                Bucket=bucket,
                CopySource={'Bucket': bucket, 'Key': key},
                Key=new_key
            )
            s3_client.delete_object(Bucket=bucket, Key=key)
        
        except Exception as e:
            # Log any errors during classification without failing the thumbnail step
            print(f"Error in classification step: {e}")
        
        # Return successful response
        return {
            'statusCode': 200,
            'body': json.dumps({
                'message': 'Thumbnail generation and classification completed successfully.',
                'thumbnail_key': thumbnail_key,
                'species': species,
                'confidence': confidence
            })
        }
    
    except Exception as e:
        # Log and return any unexpected errors
        print(f"Error generating thumbnail: {e}")
        return {
            'statusCode': 500,
            'body': json.dumps({'error': str(e)})
        }
