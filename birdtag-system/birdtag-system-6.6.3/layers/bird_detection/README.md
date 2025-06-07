# Bird Detection Lambda Layer

This Lambda layer contains all the necessary dependencies for the bird detection functionality in the BirdTag system.

## Dependencies Included

- numpy==1.26.4
- opencv-python-headless==4.9.0.80
- Pillow==10.2.0
- supervision==0.18.0
- ultralytics==8.1.28
- torch==2.2.1
- torchvision==0.17.1
- boto3==1.34.69
- botocore==1.34.69
- requests==2.31.0
- python-multipart==0.0.9

## Building the Layer

1. Make sure you have Python 3.9 installed
2. Run the build script:
   ```bash
   chmod +x build.sh
   ./build.sh
   ```
3. The script will create a `bird_detection_layer.zip` file

## Using the Layer

1. Upload the `bird_detection_layer.zip` to AWS Lambda as a new layer
2. Attach the layer to your Lambda function
3. Make sure your Lambda function's runtime is set to Python 3.9

## Notes

- The layer is built using Python 3.9
- All dependencies are installed in the `python/` directory
- The layer size is optimized by using `opencv-python-headless` instead of the full OpenCV package
- The layer includes both AWS SDK dependencies and ML-related dependencies

## Important Considerations

1. Layer Size:
   - PyTorch and its dependencies are large
   - The total layer size might exceed the default Lambda layer size limit
   - Consider using Lambda container images if the layer size is too large

2. Memory Requirements:
   - Image processing and ML operations require significant memory
   - Configure your Lambda function with at least 2048MB of memory

3. Timeout Settings:
   - Image processing can take time
   - Set the Lambda function timeout to at least 900 seconds

## Troubleshooting

If you encounter any issues:

1. Check that Python 3.9 is installed
2. Ensure you have sufficient disk space
3. Verify that all dependencies are compatible with Python 3.9
4. Check the Lambda function logs for any import errors
5. Monitor memory usage and adjust Lambda configuration if needed 