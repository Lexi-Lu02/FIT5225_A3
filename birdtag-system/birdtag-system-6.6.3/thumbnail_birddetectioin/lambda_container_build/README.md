# Bird Detection Lambda Container Deployment

This directory contains all files required to deploy a YOLO-based bird detection system as an AWS Lambda container for automated bird image analysis, part of the BirdTag Serverless Media Storage System.

## Prerequisites

- AWS CLI installed and configured
- Docker installed
- An AWS account with permissions for ECR, Lambda, S3, DynamoDB, and Cognito
- Python 3.9+ (for local testing and development)
- CUDA-capable GPU (optional, for local model training)

## Directory Structure

```
lambda_container_build/
├── Dockerfile                     # Lambda container definition
├── requirements.txt               # Python dependencies
├── lambda_function.py             # Lambda handler (YOLO image analysis)
├── test_lambda.py                 # Lambda function test script
├── test_model.py                  # Model inference test script
├── test_image.jpg                 # Example image for testing
├── test_video.mp4                 # Example video for testing
├── model.pt                       # YOLO model weights
├── cmd.sh                         # Build and deployment script
├── .dockerignore                  # Docker build exclusions
└── README.md                      # This file
```

- **model.pt**: The YOLO model weights file. The Dockerfile copies this file into the container image for the Lambda function to use at runtime.

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
     - Memory: **2048 MB** or higher (YOLO model requires significant memory)
     - Timeout: **1 minute** (image processing is typically faster than audio)
     - Set environment variables (see below)
   - Configure IAM role with minimum required permissions:
     - S3 read/write access for specific buckets
     - DynamoDB read/write access
     - CloudWatch Logs access

4. **Configure API Gateway and Cognito**
   - Create Cognito User Pool and App Client
   - Configure API Gateway with Cognito Authorizer
   - Set up CORS if needed
   - Configure API Gateway to trigger Lambda function

5. **Configure S3 Trigger**
   - Add an S3 trigger to the Lambda function
   - Set the bucket and prefix for image file uploads (e.g., `upload/image/`)
   - Configure S3 bucket policies to restrict access

6. **Set Environment Variables**
   - `DDB_TABLE` (e.g., `BirdTagMedia`)
   - `REGION` (e.g., `ap-southeast-2`)
   - `MODEL_PATH` (e.g., `model/model.pt`)
   - `LOG_LEVEL` (optional, e.g., `INFO`)
   - `COGNITO_USER_POOL_ID` (from Cognito configuration)
   - `COGNITO_CLIENT_ID` (from Cognito configuration)
   - Any other variables required by your code

## Usage

When an image file is uploaded to the configured S3 bucket, the Lambda function will:
1. Validate the request using Cognito authentication
2. Download the image from S3
3. Generate a thumbnail version (200px longest side, JPEG, 75% quality)
4. Analyze the image using YOLO model
5. Move the file to the appropriate species folder in S3
6. Write detection results and metadata to DynamoDB

## DynamoDB Record Format

The system uses a unified DynamoDB table (`BirdTagMedia`) for all media types. For images, the record format is:

```json
{
  "id": "img-uuid-001",                    // Primary key (UUID)
  "user_id": "user-abc",                   // From Cognito
  "file_type": "image",                    // Media type
  "s3_path": "species/Common Kingfisher/test_image.jpg",  // Original file path
  "thumbnail_path": "thumbnail/test_image.jpg",          // Thumbnail path
  "detected_species": ["Common Kingfisher", "House Sparrow"],  // All detected species
  "detection_boxes": [                     // YOLO detection results
    {
      "species": "Common Kingfisher",      // Species name
      "code": "comkin",                    // Species code
      "box": [0.1, 0.2, 0.3, 0.4],        // Normalized coordinates [x_min, y_min, x_max, y_max]
      "confidence": 0.9234                 // Detection confidence (0-1)
    }
  ],
  "detection_segments": null,              // Not used for images
  "detection_frames": null,                // Not used for images
  "created_at": "2024-03-15T08:30:45.123Z" // ISO8601 timestamp
}
```

## Testing

1. **Local Model Testing**
   ```bash
   python test_model.py
   ```
   This script tests the YOLO model with sample images and displays detection results.

2. **Local Lambda Testing**
   ```bash
   python test_lambda.py
   ```
   This script simulates the Lambda environment using moto for AWS service mocking.

3. **Authentication Testing**
   - Test user registration and login through Cognito
   - Verify JWT token validation
   - Test API endpoints with valid/invalid tokens

## Security Considerations

- All API endpoints are protected by Cognito authentication
- S3 buckets have restricted access policies
- DynamoDB access is limited to Lambda function role
- Environment variables are used for sensitive configuration
- CloudWatch Logs are enabled for monitoring
- API Gateway has rate limiting enabled

## Performance Considerations

- Model inference time varies based on image size and complexity
- Memory usage peaks during model inference (2GB+ recommended)
- Thumbnails are generated for efficient preview (200px longest side)
- Consider implementing image size limits or preprocessing
- Cold start performance can be improved with provisioned concurrency
- DynamoDB uses on-demand capacity mode for automatic scaling
- CloudWatch monitoring is enabled for performance tracking

## API Endpoints

The system provides the following RESTful endpoints (all require Cognito authentication):

- `GET /media/tags?tags=A,B&start_date=YYYY-MM-DD&end_date=YYYY-MM-DD&limit=N&last_key=…`
  - Query media by tags and date range
  - Supports pagination
- `GET /media/{media_id}`
  - Get detailed information for a specific media item
- `GET /media/species/{species}?limit=N&last_key=…`
  - Query media by species
  - Supports pagination

## Notes

- The container image is large due to the YOLO model and dependencies
- The model uses CPU-only inference to optimize container size
- The system supports common image formats (JPEG, PNG)
- All operations are logged to CloudWatch for monitoring
- Thumbnails are automatically generated for efficient preview
- The system follows AWS best practices for security and performance

---

For more details on the API, schema, or troubleshooting, please refer to the main project documentation or contact the maintainer. 
