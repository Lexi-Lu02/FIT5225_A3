# Use AWS Lambda Python 3.9 base image
FROM public.ecr.aws/lambda/python:3.9

# Set environment variables
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

# Install system dependencies
RUN yum update -y && \
    yum install -y \
      gcc \
      gcc-c++ \
      make \
      git \
      mesa-libGL \
      mesa-libEGL \
      libSM \
      libXrender \
      libXext \
    && yum clean all \
    && rm -rf /var/cache/yum

# Create and set working directory
WORKDIR ${LAMBDA_TASK_ROOT}

# Copy requirements first to leverage Docker cache
COPY requirements.txt .

# Install Python dependencies
# Note: We install torch with CPU-only version to reduce size
RUN pip install --no-cache-dir -r requirements.txt && \
    pip install --no-cache-dir torch torchvision --index-url https://download.pytorch.org/whl/cpu && \
    # Clean up pip cache
    rm -rf /root/.cache/pip/*

# ENV
ENV MPLCONFIGDIR=/tmp/matplotlib
ENV YOLO_CONFIG_DIR=/tmp/ultralytics

# Create model directory
RUN mkdir -p ${LAMBDA_TASK_ROOT}/model

# Copy model file (注意：model.pt 在当前目录下)
COPY model.pt ${LAMBDA_TASK_ROOT}/model/model.pt

# Copy application code
COPY lambda_function.py ${LAMBDA_TASK_ROOT}/

# Set Python path
ENV PYTHONPATH=${LAMBDA_TASK_ROOT}

# Set the CMD to your handler
CMD [ "lambda_function.lambda_handler" ]
