#!/bin/bash

# Build the Docker image
docker build -t bird_detection_layer_builder .

# Create a temporary container and copy the layer zip
docker create --name temp_container bird_detection_layer_builder
docker cp temp_container:/build/bird_detection_layer.zip .
docker rm temp_container

echo "Layer zip created successfully at bird_detection_layer.zip" 