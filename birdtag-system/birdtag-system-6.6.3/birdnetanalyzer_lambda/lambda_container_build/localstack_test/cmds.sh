#!/bin/bash

# Automatically restart the LocalStack container to ensure a clean environment
echo "Restarting LocalStack container..."
docker rm -f localstack 2>/dev/null || true

# Enable error handling
set -e
trap 'echo "Error occurred. Cleaning up..."; cleanup' ERR

# pip install awslocal jq
# sudo usermod -aG docker $USER
# newgrp docker

# Cleanup function
cleanup() {
    echo "Cleaning up AWS resources and container..."
    awslocal s3 rb s3://your-test-bucket --force || true
    awslocal dynamodb delete-table --table-name YourDDBTableName || true
    awslocal lambda delete-function --function-name birdnet-audio-analyzer || true
    awslocal ecr delete-repository --repository-name audio-analyzer --force || true
    docker stop localstack || true
    docker rm localstack || true
}

# Start LocalStack
echo "Starting LocalStack..."
docker run --rm -d \
  --name localstack \
  -p 4566:4566 -p 4571:4571 \
  -e SERVICES=s3,lambda,dynamodb,ecr \
  -e DEFAULT_REGION=ap-southeast-2 \
  -e DEBUG=1 \
  -e LAMBDA_EXECUTOR=docker \
  -e DOCKER_HOST=unix:///var/run/docker.sock \
  -v /var/run/docker.sock:/var/run/docker.sock \
  localstack/localstack

# Wait for LocalStack to be ready
echo "Waiting for LocalStack to start..."
sleep 10

# Configure AWS credentials and alias for local testing
export AWS_ACCESS_KEY_ID=test
export AWS_SECRET_ACCESS_KEY=test
export AWS_REGION=ap-southeast-2
alias awslocal="aws --endpoint-url=http://localhost:4566"

# Clean up any existing AWS resources (S3 bucket, Lambda, DynamoDB)
echo "Cleaning up old AWS resources..."
awslocal s3 rb s3://your-test-bucket --force 2>/dev/null || true
awslocal lambda delete-function --function-name birdnet-audio-analyzer 2>/dev/null || true
awslocal dynamodb delete-table --table-name YourDDBTableName 2>/dev/null || true

# Create S3 bucket
echo "Creating S3 bucket..."
awslocal s3 mb s3://your-test-bucket

# Upload test audio file
echo "Uploading test audio file..."
awslocal s3 cp test_audio.wav s3://your-test-bucket/upload/audio/test.wav

# Delete old DynamoDB table if it exists
echo "Deleting old DynamoDB table if it exists..."
awslocal dynamodb delete-table --table-name YourDDBTableName 2>/dev/null || true

# Create DynamoDB table
echo "Creating DynamoDB table..."
DDB_CREATE_OUTPUT=$(timeout 60s awslocal dynamodb create-table \
  --table-name YourDDBTableName \
  --attribute-definitions AttributeName=id,AttributeType=S \
  --key-schema AttributeName=id,KeyType=HASH \
  --provisioned-throughput ReadCapacityUnits=1,WriteCapacityUnits=1 2>&1)
DDB_CREATE_EXIT=$?
echo "$DDB_CREATE_OUTPUT"
if [ $DDB_CREATE_EXIT -ne 0 ]; then
  echo "[ERROR] Failed to create DynamoDB table. Details:"
  echo "$DDB_CREATE_OUTPUT"
  exit 1
fi

echo "DynamoDB table created successfully!"

# Create Lambda function
echo "Creating Lambda function..."
LAMBDA_CREATE_OUTPUT=$(awslocal lambda create-function \
  --function-name birdnet-audio-analyzer \
  --package-type Image \
  --code ImageUri=birdnet-lambda:latest \
  --role arn:aws:iam::000000000000:role/irrelevant \
  --timeout 300 \
  --memory-size 1024 \
  --environment Variables="{DDB_TABLE=YourDDBTableName,LOCAL_TEST=true}" 2>&1)
LAMBDA_CREATE_EXIT=$?
echo "$LAMBDA_CREATE_OUTPUT"
if [ $LAMBDA_CREATE_EXIT -ne 0 ]; then
  echo "[ERROR] Failed to create Lambda function. Details:"
  echo "$LAMBDA_CREATE_OUTPUT"
  exit 1
fi

echo "Lambda function created successfully!"

# ===== Local testing: skip S3 event source mapping steps =====
echo "[LOCAL TEST] Skipping S3 event source mapping; manually invoking Lambda for main workflow."

# Invoke Lambda function for testing
echo "Invoking Lambda function for test..."
awslocal lambda invoke \
  --function-name birdnet-audio-analyzer \
  --payload file://event.json \
  --cli-binary-format raw-in-base64-out \
  response.json

echo "Lambda response:"
cat response.json

# Verify S3 results
echo "Listing contents of S3 upload directory..."
awslocal s3 ls s3://your-test-bucket/upload/audio/

# Verify DynamoDB results
echo "Scanning DynamoDB table..."
awslocal dynamodb scan --table-name YourDDBTableName

echo "Local test completed successfully!"
