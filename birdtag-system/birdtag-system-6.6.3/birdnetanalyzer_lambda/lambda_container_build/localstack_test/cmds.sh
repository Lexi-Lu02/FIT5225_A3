#!/bin/bash

# 设置错误处理
set -e
trap 'echo "Error occurred. Cleaning up..."; cleanup' ERR

# 清理函数
cleanup() {
    echo "Cleaning up..."
    awslocal s3 rb s3://your-test-bucket --force || true
    awslocal dynamodb delete-table --table-name YourDDBTableName || true
    awslocal lambda delete-function --function-name birdnet-audio-analyzer || true
    awslocal ecr delete-repository --repository-name audio-analyzer --force || true
    docker stop localstack || true
    docker rm localstack || true
}

# 启动 LocalStack
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

# 等待 LocalStack 启动
echo "Waiting for LocalStack to start..."
sleep 10

# 设置 AWS 凭证
export AWS_ACCESS_KEY_ID=test
export AWS_SECRET_ACCESS_KEY=test
export AWS_REGION=ap-southeast-2
alias awslocal="aws --endpoint-url=http://localhost:4566"

# 创建 S3 存储桶
echo "Creating S3 bucket..."
awslocal s3 mb s3://your-test-bucket

# 上传测试音频文件
echo "Uploading test audio file..."
awslocal s3 cp ../test_audio.wav s3://your-test-bucket/upload/audio/test.wav

# 创建 DynamoDB 表
echo "Creating DynamoDB table..."
awslocal dynamodb create-table \
  --table-name YourDDBTableName \
  --attribute-definitions \
    AttributeName=id,AttributeType=S \
    AttributeName=species,AttributeType=S \
    AttributeName=created_at,AttributeType=S \
  --key-schema AttributeName=id,KeyType=HASH \
  --global-secondary-indexes \
    "[
      {
        \"IndexName\": \"species-index\",
        \"KeySchema\": [{\"AttributeName\":\"species\",\"KeyType\":\"HASH\"}],
        \"Projection\": {\"ProjectionType\":\"ALL\"},
        \"ProvisionedThroughput\": {\"ReadCapacityUnits\":1,\"WriteCapacityUnits\":1}
      },
      {
        \"IndexName\": \"created_at-index\",
        \"KeySchema\": [{\"AttributeName\":\"created_at\",\"KeyType\":\"HASH\"}],
        \"Projection\": {\"ProjectionType\":\"ALL\"},
        \"ProvisionedThroughput\": {\"ReadCapacityUnits\":1,\"WriteCapacityUnits\":1}
      }
    ]" \
  --provisioned-throughput ReadCapacityUnits=1,WriteCapacityUnits=1

# 创建 ECR 仓库
echo "Creating ECR repository..."
awslocal ecr create-repository --repository-name audio-analyzer

# 标记并推送 Docker 镜像
echo "Tagging and pushing Docker image..."
docker tag birdnet-lambda:latest localhost:4566/audio-analyzer:latest
docker push localhost:4566/audio-analyzer:latest

# 创建 Lambda 函数
echo "Creating Lambda function..."
awslocal lambda create-function \
  --function-name birdnet-audio-analyzer \
  --package-type Image \
  --code ImageUri=localhost:4566/audio-analyzer:latest \
  --role arn:aws:iam::000000000000:role/irrelevant \
  --timeout 300 \
  --memory-size 1024 \
  --environment Variables="{DDB_TABLE=YourDDBTableName,LOCAL_TEST=true}"

# 创建 S3 事件源映射
echo "Creating S3 event source mapping..."
awslocal lambda create-event-source-mapping \
  --function-name birdnet-audio-analyzer \
  --event-source-arn arn:aws:s3:::your-test-bucket \
  --starting-position LATEST

# 测试 Lambda 函数
echo "Testing Lambda function..."
awslocal lambda invoke \
  --function-name birdnet-audio-analyzer \
  --payload file://event.json response.json

# 显示结果
echo "Lambda response:"
cat response.json

# 检查 S3 结果
echo "Checking S3 results..."
awslocal s3 ls s3://your-test-bucket/species/

# 检查 DynamoDB 结果
echo "Checking DynamoDB results..."
awslocal dynamodb scan --table-name YourDDBTableName

echo "Test completed successfully!"