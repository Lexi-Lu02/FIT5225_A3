import json
import os
import boto3
import io
import uuid
import base64
from datetime import datetime
import librosa
import numpy as np
import matplotlib.pyplot as plt
import soundfile as sf

s3_client = boto3.client('s3')

def generate_waveform(audio_data, sample_rate=48000):
    """
    Generate audio waveform plot
    Args:
        audio_data: binary audio data
        sample_rate: sampling rate, default 48kHz (BirdNET standard sampling rate)
    Returns:
        BytesIO buffer containing the waveform image
    """
    try:
        # Load audio data with librosa using BirdNET standard settings
        audio_array, sr = librosa.load(
            io.BytesIO(audio_data), 
            sr=sample_rate, 
            mono=True, 
            res_type="kaiser_fast"
        )
        
        # Create waveform plot
        plt.figure(figsize=(10, 4))
        plt.plot(audio_array)
        plt.axis('off')
        
        # Set transparent background
        plt.gca().set_facecolor('none')
        plt.gcf().set_facecolor('none')
        
        # Save image to memory
        buffer = io.BytesIO()
        plt.savefig(
            buffer, 
            format='png', 
            bbox_inches='tight', 
            pad_inches=0,
            dpi=72,
            transparent=True
        )
        buffer.seek(0)
        plt.close()
        
        return buffer
    except Exception as e:
        print(f"Error generating waveform: {str(e)}")
        raise

def lambda_handler(event, context):
    """
    Lambda function to process uploaded audio files and classify them.
    Triggered by S3 ObjectCreated events.
    """
    try:
        # Get the bucket and key from the S3 event
        bucket = event['Records'][0]['s3']['bucket']['name']
        key = event['Records'][0]['s3']['object']['key']
        
        # Only process files in the upload/audio/ directory
        if not key.startswith('upload/audio/'):
            return {
                'statusCode': 200,
                'body': json.dumps('Not an audio file, skipping processing')
            }
            
        # Download the audio from S3
        response = s3_client.get_object(Bucket=bucket, Key=key)
        audio_content = response['Body'].read()
        
        # Generate waveform
        try:
            waveform_buffer = generate_waveform(audio_content)
            
            # Upload waveform to S3
            filename = os.path.basename(key)
            waveform_key = f'waveform/{os.path.splitext(filename)[0]}.png'
            s3_client.upload_fileobj(
                waveform_buffer,
                bucket,
                waveform_key,
                ExtraArgs={
                    'ContentType': 'image/png',
                    'CacheControl': 'max-age=31536000'
                }
            )
        except Exception as e:
            print(f"Error generating or uploading waveform: {str(e)}")
            waveform_key = None
        
        # =====================
        # Invoke SageMaker for bird sound classification
        # =====================
        try:
            # Convert audio to base64
            audio_b64 = base64.b64encode(audio_content).decode()
            
            # Get file extension
            file_ext = os.path.splitext(filename)[1].lower().lstrip('.')
            if file_ext not in ['wav', 'mp3']:
                file_ext = 'wav'  # default to wav format

            sagemaker = boto3.client('sagemaker-runtime')
            sm_response = sagemaker.invoke_endpoint(
                EndpointName=os.environ['SAGEMAKER_AUDIO_ENDPOINT'],
                ContentType='application/json',
                Body=json.dumps({
                    'audio': audio_b64,
                    'format': file_ext,
                    'sample_rate': 48000  # BirdNET standard sampling rate
                })
            )
            result = json.loads(sm_response['Body'].read())

            # Process SageMaker response
            if result.get('statusCode') == 200:
                detections = json.loads(result['body']).get('detections', [])
                
                # Extract labels and confidences
                labels = []
                probs = []
                for detection in detections:
                    labels.append(detection['species'])
                    probs.append(detection['confidence'])
                
                # Select the label with highest confidence
                if labels and probs:
                    max_prob_idx = probs.index(max(probs))
                    species = labels[max_prob_idx]
                    confidence = probs[max_prob_idx]
                else:
                    species = 'unknown'
                    confidence = 0.0
            else:
                species = 'unknown'
                confidence = 0.0
                labels = []
                probs = []

            # Generate unique ID
            media_id = str(uuid.uuid4())

            # Write to DynamoDB
            dynamodb = boto3.resource('dynamodb')
            item = {
                'id': media_id,
                's3_url': f's3://{bucket}/{key}',
                'media_type': 'audio',
                'tags': labels,
                'created_at': datetime.utcnow().isoformat(),
                'species': species,
                'confidence': confidence
            }
            
            # If waveform generated successfully, add waveform URL
            if waveform_key:
                item['waveform_url'] = f's3://{bucket}/{waveform_key}'
            
            table = dynamodb.Table(os.environ['DDB_TABLE'])
            table.put_item(Item=item)

            # Move file to species directory
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
                'statusCode': 500,
                'body': json.dumps({
                    'error': f'Error in classification: {str(e)}'
                })
            }
        
        return {
            'statusCode': 200,
            'body': json.dumps({
                'message': 'Audio processing and classification completed',
                'waveform_key': waveform_key,
                'species': species,
                'confidence': confidence,
                'detections': detections
            })
        }
        
    except Exception as e:
        print(f'Error processing audio: {str(e)}')
        return {
            'statusCode': 500,
            'body': json.dumps({
                'error': str(e)
            })
        }
