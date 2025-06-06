# BirdNET-Analyzer AWS Deployment Guide

## 1. Prerequisites

### 1.1 Required Files
- BirdNET-Analyzer model files:
  - `BirdNET-Analyzer-model-V2.4/model.tflite`
  - `BirdNET-Analyzer-model-V2.4/labels.txt`
- Source code files:
  - `birdnet_analyzer_lambda.py`
  - `template.yaml`
  - `requirements_birdnetanalyzer.txt`

### 1.2 Python Version
- Python 3.11 is required for BirdNET-Analyzer
- Note: This is different from the bird detection function which uses Python 3.9

### 1.3 AWS Account Setup
- AWS CLI installed and configured
- SAM CLI installed
- Appropriate AWS credentials
- Required permissions for:
  - Lambda
  - S3
  - DynamoDB
  - API Gateway
  - IAM

## 2. File Preparation

### 2.1 Model Files
1. Locate BirdNET model files:
   ```
   BirdNET-Analyzer/BirdNET-Analyzer-model-V2.4/
   ├── model.tflite
   └── labels.txt
   ```

2. Verify model files:
   ```bash
   # Check file sizes and integrity
   ls -l BirdNET-Analyzer-model-V2.4/model.tflite
   ls -l BirdNET-Analyzer-model-V2.4/labels.txt
   ```

### 2.2 Source Code
1. Create Lambda handler:
   ```python
   # birdnet_analyzer_lambda.py
   import json
   import boto3
   import librosa
   import numpy as np
   import os
   import tempfile
   from birdnet_analyzer import analyze_audio

   # Initialize AWS clients
   s3_client = boto3.client('s3')
   dynamodb = boto3.resource('dynamodb')

   # Environment variables
   MODEL_BUCKET = os.environ.get('MODEL_BUCKET')
   MEDIA_BUCKET = os.environ.get('MEDIA_BUCKET')
   DYNAMODB_TABLE = os.environ.get('DYNAMODB_TABLE')

   def lambda_handler(event, context):
       try:
           # Get audio file from S3
           bucket = event['Records'][0]['s3']['bucket']['name']
           key = event['Records'][0]['s3']['object']['key']
           
           # Download audio to temp file
           with tempfile.NamedTemporaryFile(suffix='.wav') as tmp_file:
               s3_client.download_file(bucket, key, tmp_file.name)
               
               # Analyze audio
               results = analyze_audio(tmp_file.name)
               
               # Save results to DynamoDB
               table = dynamodb.Table(DYNAMODB_TABLE)
               table.put_item(Item={
                   'fileKey': key,
                   'type': 'audio',
                   'analysisResults': results,
                   'timestamp': int(time.time())
               })
               
               return {
                   'statusCode': 200,
                   'body': json.dumps({
                       'message': 'Analysis completed',
                       'results': results
                   })
               }
               
       except Exception as e:
           print(f"Error: {str(e)}")
           return {
               'statusCode': 500,
               'body': json.dumps({'error': str(e)})
           }
   ```

2. Update template.yaml:
   ```yaml
   BirdNetAnalyzerFunction:
     Type: AWS::Serverless::Function
     Properties:
       FunctionName: !Sub birdtag-analyzer-${StudentName}
       CodeUri: src/handlers/
       Handler: birdnet_analyzer_lambda.lambda_handler
       Runtime: python3.11
       Environment:
         Variables:
           MODEL_BUCKET: !Ref ModelBucket
           MEDIA_BUCKET: !Ref MediaBucket
           DYNAMODB_TABLE: !Ref BirdTagMetadataTable
       Events:
         S3Upload:
           Type: S3
           Properties:
             Bucket: !Ref MediaBucket
             Events: s3:ObjectCreated:*
             Filter:
               S3Key:
                 Rules:
                   - Name: suffix
                     Value: .wav
   ```

3. Create requirements file:
   ```
   # requirements_birdnetanalyzer.txt
   # Python 3.11 required
   boto3>=1.28.0
   librosa>=0.10.0
   numpy>=1.24.0
   tensorflow>=2.13.0
   soundfile>=0.12.1
   botocore>=1.31.0
   ```

## 3. AWS Deployment Steps

### 3.1 Create S3 Buckets
1. Create Model Bucket (if not exists):
   ```bash
   aws s3 mb s3://birdtag-models-${YOUR_NAME}-${AWS_ACCOUNT_ID}
   ```

2. Create Media Bucket (if not exists):
   ```bash
   aws s3 mb s3://birdtag-media-${YOUR_NAME}-${AWS_ACCOUNT_ID}
   ```

### 3.2 Upload Model Files
1. Upload model files to S3:
   ```bash
   aws s3 cp BirdNET-Analyzer-model-V2.4/model.tflite s3://birdtag-models-${YOUR_NAME}-${AWS_ACCOUNT_ID}/birdnet/model.tflite
   aws s3 cp BirdNET-Analyzer-model-V2.4/labels.txt s3://birdtag-models-${YOUR_NAME}-${AWS_ACCOUNT_ID}/birdnet/labels.txt
   ```

2. Verify uploads:
   ```bash
   aws s3 ls s3://birdtag-models-${YOUR_NAME}-${AWS_ACCOUNT_ID}/birdnet/
   ```

### 3.3 Create Lambda Layer
1. Create layer directory:
   ```bash
   mkdir -p layers/birdnet_analyzer/python
   cd layers/birdnet_analyzer
   ```

2. Install dependencies (using Python 3.11):
   ```bash
   python3.11 -m pip install -r requirements.txt -t python/
   ```

3. Create layer zip:
   ```bash
   zip -r ../layer.zip .
   ```

4. Create Lambda layer:
   ```bash
   aws lambda publish-layer-version \
     --layer-name birdnet-analyzer-deps \
     --description "Dependencies for BirdNET-Analyzer" \
     --zip-file fileb://../layer.zip \
     --compatible-runtimes python3.11
   ```

### 3.4 Deploy SAM Application
1. Build the application:
   ```bash
   sam build
   ```

2. Deploy the application:
   ```bash
   sam deploy --guided
   ```
   When prompted, provide:
   - Stack name: birdtag-analyzer
   - AWS Region: your-region
   - StudentName: your-name
   - Confirm changes: yes

## 4. Testing Deployment

### 4.1 Test Audio Upload
1. Upload test audio:
   ```bash
   aws s3 cp test.wav s3://birdtag-media-${YOUR_NAME}-${AWS_ACCOUNT_ID}/uploads/
   ```

2. Check Lambda logs:
   ```bash
   aws logs get-log-events \
     --log-group-name /aws/lambda/birdtag-analyzer-${YOUR_NAME} \
     --log-stream-name $(aws logs describe-log-streams \
       --log-group-name /aws/lambda/birdtag-analyzer-${YOUR_NAME} \
       --query 'logStreams[0].logStreamName' \
       --output text)
   ```

### 4.2 Verify Results
1. Check DynamoDB for analysis results:
   ```bash
   aws dynamodb scan \
     --table-name BirdTagMetadata-${YOUR_NAME}
   ```

## 5. Troubleshooting

### 5.1 Common Issues
1. Memory Issues
   - Increase Lambda memory to 2048MB
   - Optimize audio processing
   - Check model loading

2. Timeout Issues
   - Increase Lambda timeout
   - Optimize audio processing
   - Consider audio length limits

3. Model Loading Issues
   - Verify model file integrity
   - Check model file permissions
   - Verify model version compatibility

4. Python Version Issues
   - Ensure using Python 3.11
   - Check Lambda layer compatibility
   - Verify runtime settings

### 5.2 Debug Commands
1. Check Lambda status:
   ```bash
   aws lambda get-function \
     --function-name birdtag-analyzer-${YOUR_NAME}
   ```

2. View CloudWatch metrics:
   ```bash
   aws cloudwatch get-metric-statistics \
     --namespace AWS/Lambda \
     --metric-name Duration \
     --dimensions Name=FunctionName,Value=birdtag-analyzer-${YOUR_NAME} \
     --start-time $(date -u +"%Y-%m-%dT%H:%M:%SZ" -d "-1 hour") \
     --end-time $(date -u +"%Y-%m-%dT%H:%M:%SZ") \
     --period 300 \
     --statistics Average
   ```

## 6. Maintenance

### 6.1 Regular Checks
- Monitor CloudWatch metrics
- Check Lambda logs
- Verify S3 bucket usage
- Review DynamoDB table size

### 6.2 Updates
1. Update code:
   ```bash
   git pull
   sam build
   sam deploy
   ```

2. Update dependencies:
   ```bash
   pip install -r requirements_birdnetanalyzer.txt --upgrade
   # Recreate and update Lambda layer
   ```

### 6.3 Backup
1. Backup model files:
   ```bash
   aws s3 cp s3://birdtag-models-${YOUR_NAME}-${AWS_ACCOUNT_ID}/birdnet/model.tflite ./model.tflite.backup
   aws s3 cp s3://birdtag-models-${YOUR_NAME}-${AWS_ACCOUNT_ID}/birdnet/labels.txt ./labels.txt.backup
   ```

2. Backup DynamoDB:
   ```bash
   aws dynamodb export-table-to-point-in-time \
     --table-name BirdTagMetadata-${YOUR_NAME} \
     --s3-bucket your-backup-bucket
   ``` 