FROM public.ecr.aws/lambda/python:3.9

# Set working directory
WORKDIR /build

# Copy requirements file
COPY requirements.txt .

# Install dependencies
RUN pip install -r requirements.txt -t python/

# Create layer zip
RUN zip -r bird_detection_layer.zip python/

# The layer zip will be in /build/bird_detection_layer.zip 