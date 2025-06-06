#!/bin/bash

# Create python directory
mkdir -p python

# Install dependencies
pip install -r requirements.txt -t python/

# Copy model files
mkdir -p python/model
cp model/model.tflite python/model/
cp model/labels.txt python/model/

# Create layer zip
zip -r birdnet_analyzer_layer.zip python/

echo "Layer zip created successfully at birdnet_analyzer_layer.zip" 