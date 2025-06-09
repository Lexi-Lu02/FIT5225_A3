#!/bin/bash

# 设置变量
IMAGE_NAME="bird-detection-lambda"
IMAGE_TAG="latest"
AWS_REGION="us-east-1"
AWS_ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)

# 构建Docker镜像
echo "Building Docker image..."
docker build -t ${IMAGE_NAME}:${IMAGE_TAG} .

# 测试镜像
echo "Testing Docker image locally..."
docker run --rm -v $(pwd)/test_image.jpg:/var/task/test_image.jpg \
    -e LOCAL_TEST=1 \
    -e DDB_TABLE=BirdTagMedia \
    -e MODEL_PATH=model/model.pt \
    ${IMAGE_NAME}:${IMAGE_TAG} \
    '{"Records": [{"s3": {"bucket": {"name": "test-bucket"}, "object": {"key": "test_image.jpg"}}}]}'

# 登录到Amazon ECR
echo "Logging in to Amazon ECR..."
aws ecr get-login-password --region ${AWS_REGION} | docker login --username AWS --password-stdin ${AWS_ACCOUNT_ID}.dkr.ecr.${AWS_REGION}.amazonaws.com

# 创建ECR仓库（如果不存在）
echo "Creating ECR repository if it doesn't exist..."
aws ecr describe-repositories --repository-names ${IMAGE_NAME} || \
    aws ecr create-repository --repository-name ${IMAGE_NAME}

# 标记镜像
echo "Tagging image for ECR..."
docker tag ${IMAGE_NAME}:${IMAGE_TAG} ${AWS_ACCOUNT_ID}.dkr.ecr.${AWS_REGION}.amazonaws.com/${IMAGE_NAME}:${IMAGE_TAG}

# 推送镜像到ECR
echo "Pushing image to ECR..."
docker push ${AWS_ACCOUNT_ID}.dkr.ecr.${AWS_REGION}.amazonaws.com/${IMAGE_NAME}:${IMAGE_TAG}

# 更新Lambda函数配置（如果函数已存在）
echo "Updating Lambda function configuration..."
aws lambda update-function-configuration \
    --function-name bird-detection \
    --environment "Variables={MODEL_PATH=model/model.pt,DDB_TABLE=BirdTagMedia}" \
    --region ${AWS_REGION} || echo "Note: Lambda function may not exist yet. Please create it with these environment variables."

echo "Done! Image pushed to ECR: ${AWS_ACCOUNT_ID}.dkr.ecr.${AWS_REGION}.amazonaws.com/${IMAGE_NAME}:${IMAGE_TAG}"
echo "Remember to set these environment variables in your Lambda function:"
echo "  MODEL_PATH=model/model.pt"
echo "  DDB_TABLE=BirdTagMedia"
