# Use the AWS Lambda Python 3.11 base image
FROM public.ecr.aws/lambda/python:3.11

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONPATH=/var/task

# Install system dependencies
RUN yum update -y && \
    yum install -y \
    gcc \
    gcc-c++ \
    make \
    ffmpeg \
    libsndfile \
    fftw \
    && yum clean all

# Copy requirements file
COPY requirements.txt ${LAMBDA_TASK_ROOT}

# Install Python dependencies
RUN pip install --no-cache-dir --only-binary :all: numpy==1.24.3 && \
    pip install --no-cache-dir -r requirements.txt && \
    pip install --no-cache-dir aws-lambda-powertools

# Copy function code
COPY lambda_function.py ${LAMBDA_TASK_ROOT}

# Copy BirdNET model and necessary files
COPY BirdNET-Analyzer-model-V2.4/V2.4 ${LAMBDA_TASK_ROOT}/birdnet_analyzer/checkpoints/V2.4
COPY birdnet_analyzer ${LAMBDA_TASK_ROOT}/birdnet_analyzer

# Set permissions
RUN chmod -R 755 ${LAMBDA_TASK_ROOT}

# Set the CMD to your handler
CMD [ "lambda_function.lambda_handler" ] 
