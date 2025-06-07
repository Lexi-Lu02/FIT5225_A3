# BirdNET-Analyzer Lambda Layer

This Lambda layer contains all the necessary dependencies for the BirdNET-Analyzer functionality in the BirdTag system.

## Dependencies Included

- librosa==0.10.1
- resampy==0.4.2
- tflite-runtime==2.15.0
- scikit-learn==1.6.1
- tqdm==4.66.1
- numpy==1.26.4
- soundfile==0.12.1
- boto3==1.34.69
- botocore==1.34.69
- requests==2.31.0
- python-multipart==0.0.9

## Building the Layer

1. Make sure you have Python 3.11 installed
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

- The layer is built using Python 3.11
- All dependencies are installed in the `python/` directory
- The layer includes both AWS SDK dependencies and audio processing dependencies
- The model files are included in the `python/model/` directory

## Important Considerations

1. Layer Size:
   - Using tflite-runtime instead of full TensorFlow reduces the layer size
   - The total layer size should be within Lambda layer size limits
   - If size is still an issue, consider using Lambda container images

2. Memory Requirements:
   - Audio processing and ML operations require significant memory
   - Configure your Lambda function with at least 2048MB of memory
   - Consider using provisioned concurrency for better performance

3. Timeout Settings:
   - Audio processing can take time
   - Set the Lambda function timeout to at least 900 seconds
   - Consider the size of audio files being processed

4. Performance Optimization:
   - Use provisioned concurrency to reduce cold start times
   - Monitor memory usage and adjust configuration if needed
   - The INT8 quantized model is used for better performance

## Troubleshooting

If you encounter any issues:

1. Check that Python 3.11 is installed
2. Ensure you have sufficient disk space
3. Verify that all dependencies are compatible with Python 3.11
4. Check the Lambda function logs for any import errors
5. Monitor memory usage and adjust Lambda configuration if needed
6. Check CloudWatch metrics for performance issues 