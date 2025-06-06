# Bird Detection AWS Deployment Guide

## 1. Prerequisites

### 1.1 Required Files
- YOLO model file (`model.pt`)
- Source code files:
  - `bird_detection_lambda.py`
  - `template.yaml`
  - `requirements.txt`

### 1.2 AWS Account Setup
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

### 2.1 Model File
1. Locate your YOLO model file:
   ```
   bird_detection/model.pt
   ```

2. Verify model file:
   ```bash
   # Check file size and integrity
   ls -l model.pt
   ```

### 2.2 Source Code
1. Ensure all required files are in correct locations:
   ```
   birdtag-system/
   ├── src/
   │   └── handler/
   │       └── bird_detection_lambda.py
   ├── template.yaml
   └── requirements.txt
   ```

2. Verify file permissions:
   ```bash
   chmod 644 src/handler/bird_detection_lambda.py
   chmod 644 template.yaml
   chmod 644 requirements.txt
   ```

## 3. AWS Deployment Steps

### 3.1 Create S3 Buckets
1. Create Model Bucket:
   ```bash
   aws s3 mb s3://birdtag-models-${YOUR_NAME}-${AWS_ACCOUNT_ID}
   ```

2. Create Media Bucket:
   ```bash
   aws s3 mb s3://birdtag-media-${YOUR_NAME}-${AWS_ACCOUNT_ID}
   ```

### 3.2 Upload Model File
1. Upload model to S3:
   ```bash
   aws s3 cp model.pt s3://birdtag-models-${YOUR_NAME}-${AWS_ACCOUNT_ID}/model.pt
   ```

2. Verify upload:
   ```bash
   aws s3 ls s3://birdtag-models-${YOUR_NAME}-${AWS_ACCOUNT_ID}/
   ```

### 3.3 Create Lambda Layer
1. Create a directory for layer:
   ```bash
   mkdir -p lambda-layer/python
   cd lambda-layer
   ```

2. Install dependencies:
   ```bash
   pip install -r ../requirements.txt -t python/
   ```

3. Create layer zip:
   ```bash
   zip -r ../layer.zip .
   ```

4. Create Lambda layer:
   ```bash
   aws lambda publish-layer-version \
     --layer-name bird-detection-deps \
     --description "Dependencies for bird detection" \
     --zip-file fileb://../layer.zip
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
   - Stack name: birdtag-detection
   - AWS Region: your-region
   - StudentName: your-name
   - Confirm changes: yes

## 4. Post-Deployment Configuration

### 4.1 Environment Variables
Verify Lambda function environment variables:
```bash
aws lambda get-function-configuration \
  --function-name birdtag-detection-${YOUR_NAME}
```

Required variables:
- MODEL_BUCKET
- MODEL_KEY
- MEDIA_BUCKET
- DYNAMODB_TABLE

### 4.2 IAM Permissions
Verify Lambda execution role has:
- S3 read/write permissions
- DynamoDB read/write permissions
- CloudWatch Logs permissions

### 4.3 API Gateway Configuration
1. Get API endpoint:
   ```bash
   aws apigateway get-rest-apis
   ```

2. Test the endpoint:
   ```bash
   curl -X POST \
     https://${API_ID}.execute-api.${REGION}.amazonaws.com/dev/v1/detect \
     -H 'Content-Type: application/json' \
     -d '{"bucket":"your-bucket","key":"test.jpg"}'
   ```

## 5. Testing Deployment

### 5.1 Test Image Upload
1. Upload test image:
   ```bash
   aws s3 cp test.jpg s3://birdtag-media-${YOUR_NAME}-${AWS_ACCOUNT_ID}/uploads/
   ```

2. Check Lambda logs:
   ```bash
   aws logs get-log-events \
     --log-group-name /aws/lambda/birdtag-detection-${YOUR_NAME} \
     --log-stream-name $(aws logs describe-log-streams \
       --log-group-name /aws/lambda/birdtag-detection-${YOUR_NAME} \
       --query 'logStreams[0].logStreamName' \
       --output text)
   ```

### 5.2 Verify Results
1. Check S3 for processed image:
   ```bash
   aws s3 ls s3://birdtag-media-${YOUR_NAME}-${AWS_ACCOUNT_ID}/results/
   ```

2. Check DynamoDB for detection results:
   ```bash
   aws dynamodb scan \
     --table-name BirdTagMetadata-${YOUR_NAME}
   ```

## 6. Troubleshooting

### 6.1 Common Issues
1. Lambda Timeout
   - Check image size
   - Increase Lambda timeout
   - Optimize model loading

2. Memory Issues
   - Increase Lambda memory
   - Check model size
   - Optimize image processing

3. Permission Errors
   - Verify IAM roles
   - Check bucket policies
   - Review Lambda execution role

### 6.2 Debug Commands
1. Check Lambda status:
   ```bash
   aws lambda get-function \
     --function-name birdtag-detection-${YOUR_NAME}
   ```

2. View CloudWatch metrics:
   ```bash
   aws cloudwatch get-metric-statistics \
     --namespace AWS/Lambda \
     --metric-name Duration \
     --dimensions Name=FunctionName,Value=birdtag-detection-${YOUR_NAME} \
     --start-time $(date -u +"%Y-%m-%dT%H:%M:%SZ" -d "-1 hour") \
     --end-time $(date -u +"%Y-%m-%dT%H:%M:%SZ") \
     --period 300 \
     --statistics Average
   ```

## 7. Maintenance

### 7.1 Regular Checks
- Monitor CloudWatch metrics
- Check Lambda logs
- Verify S3 bucket usage
- Review DynamoDB table size

### 7.2 Updates
1. Update code:
   ```bash
   git pull
   sam build
   sam deploy
   ```

2. Update dependencies:
   ```bash
   pip install -r requirements.txt --upgrade
   # Recreate and update Lambda layer
   ```

### 7.3 Backup
1. Backup model:
   ```bash
   aws s3 cp s3://birdtag-models-${YOUR_NAME}-${AWS_ACCOUNT_ID}/model.pt ./model.pt.backup
   ```

2. Backup DynamoDB:
   ```bash
   aws dynamodb export-table-to-point-in-time \
     --table-name BirdTagMetadata-${YOUR_NAME} \
     --s3-bucket your-backup-bucket
   ``` 