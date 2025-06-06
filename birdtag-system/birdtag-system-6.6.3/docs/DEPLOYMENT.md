# BirdTag Deployment Guide

## Prerequisites
- AWS CLI installed and configured
- Python 3.9 and 3.11 installed
- SAM CLI installed
- Docker installed (for local testing)

## Local Development Setup

1. Clone the repository:
```bash
git clone <repository-url>
cd birdtag-system
```

2. Create and activate virtual environments:
```bash
# For Python 3.9
python3.9 -m venv venv39
source venv39/bin/activate
pip install -r requirements.txt

# For Python 3.11
python3.11 -m venv venv311
source venv311/bin/activate
pip install -r requirements.txt
```

3. Build layers:
```bash
cd layers
./build_layers.sh
```

4. Run tests:
```bash
pytest tests/
```

## Deployment Steps

1. Build the application:
```bash
sam build
```

2. Deploy the application:
```bash
sam deploy --guided
```

3. Follow the prompts to provide:
   - Stack name
   - AWS Region
   - Student name (for resource naming)
   - Confirm changes before deploy
   - Allow SAM CLI IAM role creation
   - Save arguments to configuration file

4. After deployment, note the outputs:
   - UserPoolId
   - UserPoolClientId
   - ApiGatewayUrl
   - MediaBucketName
   - ModelBucketName
   - DynamoDBTableName
   - CognitoHostedUIUrl

## Post-Deployment Steps

1. Upload model files to the ModelBucket:
```bash
aws s3 cp model.pt s3://<ModelBucketName>/model.pt
aws s3 cp labels.txt s3://<ModelBucketName>/labels.txt
```

2. Configure CORS for the MediaBucket:
```bash
aws s3api put-bucket-cors --bucket <MediaBucketName> --cors-configuration file://cors.json
```

3. Test the API endpoints using the provided Postman collection.

## Monitoring and Maintenance

1. View CloudWatch Logs:
```bash
aws logs get-log-events --log-group-name /aws/lambda/birdtag-<function-name>
```

2. Monitor DynamoDB metrics in CloudWatch.

3. Check API Gateway metrics for endpoint performance.

## Troubleshooting

1. Check Lambda function logs in CloudWatch.
2. Verify IAM permissions.
3. Ensure environment variables are set correctly.
4. Check S3 bucket permissions.
5. Verify API Gateway configuration. 