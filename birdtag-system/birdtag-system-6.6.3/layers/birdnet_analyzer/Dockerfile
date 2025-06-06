FROM public.ecr.aws/lambda/python:3.11

# Set working directory
WORKDIR /build

# Install system dependencies
RUN yum update -y && \
    yum install -y gcc gcc-c++ make && \
    yum clean all

# Copy requirements file
COPY requirements.txt .
COPY model/ python/model/

# Install dependencies
RUN pip install -r requirements.txt -t python/

# Create layer zip
RUN zip -r birdnet_analyzer_layer.zip python/

# The layer zip will be in /build/birdnet_analyzer_layer.zip 