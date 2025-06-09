#!/bin/bash

# 自动重启 localstack 容器，确保环境干净
echo "Restarting localstack container..."
docker rm -f localstack 2>/dev/null || true

# 设置错误处理
set -e
trap 'echo "Error occurred. Cleaning up..."; cleanup' ERR

# pip install awslocal jq

# sudo usermod -aG docker $USER

# newgrp docker

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

# 清理旧的 AWS 资源（S3 桶、Lambda 函数、DynamoDB 表）
echo "Cleaning up old AWS resources..."
awslocal s3 rb s3://your-test-bucket --force 2>/dev/null || true
awslocal lambda delete-function --function-name birdnet-audio-analyzer 2>/dev/null || true
awslocal dynamodb delete-table --table-name YourDDBTableName 2>/dev/null || true

# 创建 S3 存储桶
echo "Creating S3 bucket..."
awslocal s3 mb s3://your-test-bucket

# 上传测试音频文件
echo "Uploading test audio file..."
awslocal s3 cp test_audio.wav s3://your-test-bucket/upload/audio/test.wav

# 删除旧的 DynamoDB 表（如果存在）
echo "Deleting old DynamoDB table if exists..."
awslocal dynamodb delete-table --table-name YourDDBTableName 2>/dev/null || true

# 创建 DynamoDB 表
echo "Creating DynamoDB table..."
DDB_CREATE_OUTPUT=$(timeout 60s awslocal dynamodb create-table \
  --table-name YourDDBTableName \
  --attribute-definitions AttributeName=id,AttributeType=S \
  --key-schema AttributeName=id,KeyType=HASH \
  --provisioned-throughput ReadCapacityUnits=1,WriteCapacityUnits=1 2>&1)
DDB_CREATE_EXIT=$?
echo "$DDB_CREATE_OUTPUT"
if [ $DDB_CREATE_EXIT -ne 0 ]; then
  echo "[错误] DynamoDB 表创建失败，错误信息如下："
  echo "$DDB_CREATE_OUTPUT"
  exit 1
fi

echo "DynamoDB table created!"

# 创建 Lambda 函数
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
  echo "[错误] Lambda 函数创建失败，错误信息如下："
  echo "$LAMBDA_CREATE_OUTPUT"
  exit 1
fi

echo "Lambda function created!"

# ===== 本地测试跳过 S3 事件源映射相关步骤 =====
echo "[本地测试] 跳过 S3 事件源映射创建，仅手动触发 Lambda 测试主流程。"

# 手动触发 Lambda 函数测试
echo "Testing Lambda function..."
awslocal lambda invoke \
  --function-name birdnet-audio-analyzer \
  --payload file://event.json \
  --cli-binary-format raw-in-base64-out \
  response.json

echo "Lambda response:"
cat response.json

# 检查 S3 结果
echo "Checking S3 results..."
awslocal s3 ls s3://your-test-bucket/upload/audio/

# 检查 DynamoDB 结果
echo "Checking DynamoDB results..."
awslocal dynamodb scan --table-name YourDDBTableName

echo "Test completed successfully!"
