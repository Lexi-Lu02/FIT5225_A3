# Use AWS Lambda Python 3.9 base image
FROM public.ecr.aws/lambda/python:3.9

# Set environment variables for Python optimization and pip configuration
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

# Install system dependencies required for building and running the application
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

# Create and set working directory to Lambda task root
WORKDIR ${LAMBDA_TASK_ROOT}

# Copy requirements first to leverage Docker cache for faster builds
COPY requirements.txt .

# Install Python dependencies
# Install PyTorch CPU-only version to optimize container size
RUN pip install --no-cache-dir -r requirements.txt && \
    pip install --no-cache-dir torch torchvision --index-url https://download.pytorch.org/whl/cpu && \
    # Clean up pip cache to reduce image size
    rm -rf /root/.cache/pip/*

# Set environment variables for matplotlib and YOLO configuration
ENV MPLCONFIGDIR=/tmp/matplotlib
ENV YOLO_CONFIG_DIR=/tmp/ultralytics

# Create model directory for storing the YOLO model
RUN mkdir -p ${LAMBDA_TASK_ROOT}/model

# Copy YOLO model file (Note: model.pt should be present in the build context)
COPY model.pt ${LAMBDA_TASK_ROOT}/model/model.pt

# Copy Lambda function handler code
COPY lambda_function.py ${LAMBDA_TASK_ROOT}/

# Set Python path to include Lambda task root
ENV PYTHONPATH=${LAMBDA_TASK_ROOT}

# Set the Lambda handler function as the container entrypoint
CMD [ "lambda_function.lambda_handler" ]
