# 使用 Python 3.11 作为基础镜像
FROM python:3.11-slim

# 设置工作目录
WORKDIR /opt/ml/code

# 安装系统依赖
RUN apt-get update && apt-get install -y \
    ffmpeg \
    libsndfile1 \
    && rm -rf /var/lib/apt/lists/*

# 复制依赖文件
COPY requirements.txt .

# 安装 Python 依赖
RUN pip install --no-cache-dir -r requirements.txt

# 创建必要的目录
RUN mkdir -p /opt/ml/model

# 复制模型和代码
COPY model/ /opt/ml/model/
COPY inference.py .

# 设置环境变量
ENV PYTHONUNBUFFERED=TRUE
ENV PYTHONDONTWRITEBYTECODE=TRUE
ENV PATH="/opt/ml/code:${PATH}"
ENV SAGEMAKER_BATCH=True
ENV SAGEMAKER_MAX_PAYLOAD_IN_MB=6
ENV SAGEMAKER_MAX_CONCURRENT_TRANSFORMS=1

# 设置 SageMaker 服务端口
EXPOSE 8080

# 设置入口点
ENTRYPOINT ["python","inference.py"]
