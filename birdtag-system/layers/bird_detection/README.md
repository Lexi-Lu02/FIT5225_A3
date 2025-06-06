# Bird Detection Lambda Layer

This Lambda layer contains all the necessary dependencies for the bird detection functionality in the BirdTag system.

## Dependencies Included

- numpy==1.24.3
- opencv-python-headless==4.8.1.78
- Pillow==10.0.0
- supervision==0.18.0
- ultralytics==8.0.196
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
3. The script will create a `bird_detection_layer.zip` file

## Using the Layer

1. Upload the `bird_detection_layer.zip` to AWS Lambda as a new layer
2. Attach the layer to your Lambda function
3. Make sure your Lambda function's runtime is set to Python 3.9

## Notes

- The layer is built using the official AWS Lambda Python 3.9 base image
- All dependencies are installed in the `python/` directory
- The layer size is optimized by using `opencv-python-headless` instead of the full OpenCV package
- The layer includes both AWS SDK dependencies and ML-related dependencies

## Troubleshooting

If you encounter any issues:

1. Check that Docker is running
2. Ensure you have sufficient disk space
3. Verify that all dependencies are compatible with Python 3.9
4. Check the Lambda function logs for any import errors 