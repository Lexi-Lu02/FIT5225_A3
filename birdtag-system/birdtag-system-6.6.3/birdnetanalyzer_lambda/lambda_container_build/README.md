# BirdNET Lambda Container

This directory contains the necessary files to deploy BirdNET as an AWS Lambda container.

## Prerequisites

1. AWS CLI installed and configured
2. Docker installed
3. AWS account with appropriate permissions
4. Python 3.11

## Directory Structure

```
lambda_birdnet/
├── Dockerfile              # Container definition
├── requirements.txt        # Python dependencies
├── lambda_function.py      # Lambda handler
├── build_and_deploy.sh     # Build and deployment script
└── README.md              # This file
```

## Deployment Steps

1. Set your AWS account ID in the build_and_deploy.sh script:
   ```bash
   export AWS_ACCOUNT_ID="your-account-id"
   ```

2. Make the build script executable:
   ```bash
   chmod +x build_and_deploy.sh
   ```

3. Run the build and deploy script:
   ```bash
   ./build_and_deploy.sh
   ```

4. Create a new Lambda function in AWS Console:
   - Choose "Container image" as the source
   - Select the image from ECR
   - Configure the following settings:
     - Memory: 1024 MB (minimum)
     - Timeout: 5 minutes
     - Environment variables (if needed)

5. Configure S3 trigger:
   - Add S3 trigger to the Lambda function
   - Configure the bucket and prefix for audio files

## Usage

The Lambda function will be triggered when an audio file is uploaded to the configured S3 bucket. It will:
1. Download the audio file
2. Process it using BirdNET
3. Return the detection results

## Response Format

```json
{
    "statusCode": 200,
    "body": {
        "message": "Success",
        "results": [
            {
                "species": "bird_species_name",
                "confidence": 0.95,
                "start_time": 0.0,
                "end_time": 3.0
            }
        ],
        "audio_info": {
            "duration": 180.0,
            "sample_rate": 44100,
            "channels": 1
        }
    }
}
```

## Notes

- The container image size is large due to the BirdNET model and dependencies
- Make sure to allocate enough memory and timeout for the Lambda function
- Consider using provisioned concurrency for better performance 