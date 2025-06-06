#!/bin/bash

# Build the Docker image
docker build -t birdnet_analyzer_layer_builder .

# Create a temporary container and copy the layer zip
docker create --name temp_container birdnet_analyzer_layer_builder
docker cp temp_container:/build/birdnet_analyzer_layer.zip .
docker rm temp_container

echo "Layer zip created successfully at birdnet_analyzer_layer.zip" 