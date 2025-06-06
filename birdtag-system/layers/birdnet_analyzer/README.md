# BirdNET-Analyzer Lambda Layer

This Lambda layer contains all the necessary dependencies for the BirdNET-Analyzer functionality in the BirdTag system.

## Dependencies Included

- librosa==0.10.1
- resampy==0.4.2
- tensorflow==2.15.1
- scikit-learn==1.6.1
- tqdm==4.66.1
- numpy==1.24.3
- soundfile==0.12.1
- boto3==1.28.38
- botocore==1.31.38
- requests==2.31.0
- python-multipart==0.0.6

## Building the Layer

1. Make sure you have Docker installed and running
2. Run the build script:
   ```bash
   chmod +x build.sh
   ./build.sh
   ```
3. The script will create a `birdnet_analyzer_layer.zip` file

## Using the Layer

1. Upload the `birdnet_analyzer_layer.zip` to AWS Lambda as a new layer
2. Attach the layer to your Lambda function
3. Make sure your Lambda function's runtime is set to Python 3.11

## Notes

- The layer is built using the official AWS Lambda Python 3.11 base image
- All dependencies are installed in the `python/` directory
- The layer includes both AWS SDK dependencies and audio processing dependencies
- System-level dependencies (gcc, gcc-c++, make) are installed during the build process

## Important Considerations

1. Layer Size:
   - TensorFlow and its dependencies are large
   - The total layer size might exceed the default Lambda layer size limit
   - Consider using Lambda container images if the layer size is too large

2. Memory Requirements:
   - Audio processing and ML operations require significant memory
   - Configure your Lambda function with at least 2048MB of memory

3. Timeout Settings:
   - Audio processing can take time
   - Set the Lambda function timeout to at least 900 seconds

## Troubleshooting

If you encounter any issues:

1. Check that Docker is running
2. Ensure you have sufficient disk space
3. Verify that all dependencies are compatible with Python 3.11
4. Check the Lambda function logs for any import errors
5. Monitor memory usage and adjust Lambda configuration if needed 