# BirdNET Lambda Container Deployment

This directory contains all files required to deploy BirdNET-Analyzer as an AWS Lambda container for automated bird audio analysis.

## Prerequisites

- AWS CLI installed and configured
- Docker installed
- An AWS account with permissions for ECR, Lambda, S3, and DynamoDB
- Python 3.9+ (for local testing and development)

## Directory Structure

```
lambda_container_build/
├── Dockerfile                     # Lambda container definition
├── requirements.txt               # Python dependencies
├── lambda_function.py             # Lambda handler (BirdNET audio analysis)
├── test.py                        # Local test script
├── test_audio.wav                 # Example audio file for testing
├── cmd.sh                         # Build and deployment script
├── BirdNET-Analyzer-model-V2.4/   # BirdNET model files (e.g., .tflite)
├── birdnet_analyzer/              # BirdNET source code
├── localstack_test/               # LocalStack test utilities
└── README.md                      # This file
```

- **BirdNET-Analyzer-model-V2.4/**: This directory must contain the required BirdNET model file(s), e.g., `BirdNET_GLOBAL_2.4_Model_FP32.tflite`. The Dockerfile should COPY this directory into the container image so the Lambda function can access the model at runtime.

## Deployment Steps

1. **Set AWS Account ID and ECR Repository**
   - Edit `cmd.sh` and set your AWS account ID and ECR repository name if needed.

2. **Build the Docker Image**
   ```bash
   chmod +x cmd.sh
   ./cmd.sh
   ```
   This script will:
   - Build the Docker image
   - Tag and push it to your ECR repository

3. **Create Lambda Function in AWS Console**
   - Choose "Container image" as the source
   - Select the image from your ECR repository
   - Recommended settings:
     - Memory: **1024 MB** or higher (BirdNET is resource-intensive)
     - Timeout: **5 minutes** or more
     - Set environment variables (see below)

4. **Configure S3 Trigger**
   - Add an S3 trigger to the Lambda function
   - Set the bucket and prefix for audio file uploads (e.g., `upload/audio/`)

5. **Set Environment Variables**
   - `DDB_TABLE` (e.g., `BirdTagMedia`)
   - `REGION` (e.g., `ap-southeast-2`)
   - `MODEL_PATH` (e.g., `BirdNET-Analyzer-model-V2.4/BirdNET_GLOBAL_2.4_Model_FP32.tflite`)
   - `LOG_LEVEL` (optional, e.g., `INFO`)
   - Any other variables required by your code

## Usage

When an audio file is uploaded to the configured S3 bucket, the Lambda function will:
1. Download the audio file from S3
2. Analyze it using BirdNET
3. Move the file to the appropriate species folder in S3
4. Write detection results and metadata to DynamoDB

## DynamoDB Record Format

See `../db/db_schema.md` for the full schema. Example for audio:
```json
{
  "id": "aud-uuid-002",
  "user_id": "user-def",
  "file_type": "audio",
  "s3_path": "species/Black-capped Chickadee/test_audio.wav",
  "thumbnail_path": null,
  "detected_species": ["Black-capped Chickadee", "House Finch"],
  "detection_boxes": null,
  "detection_segments": [
    {
      "species": "Black-capped Chickadee",
      "code": "bkcchi",
      "start": 0.0,
      "end": 3.0,
      "confidence": 0.8141
    }
  ],
  "detection_frames": null,
  "created_at": "2024-06-01T12:34:56.789Z"
}
```

## Notes

- The container image is large due to the BirdNET model and dependencies.
- Ensure your Lambda function has sufficient memory and timeout.
- If you see errors about missing libraries (e.g., `libGL.so.1`), add `RUN yum install -y mesa-libGL` to your Dockerfile.
- The Dockerfile must COPY the BirdNET-Analyzer-model-V2.4/ directory into the image for the model to be available at runtime.
- For best cold start performance, consider using provisioned concurrency.
- For local testing, use `test.py` and set `LOCAL_TEST=1` in your environment variables.

---

If you need more details on the API, schema, or troubleshooting, please refer to the main project documentation or contact the maintainer. 
