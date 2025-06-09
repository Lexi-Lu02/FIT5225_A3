# Bird Detection System User Guide

This guide provides step-by-step instructions for using the Bird Detection System, including authentication, media upload (images and videos), processing, and result querying.

## Table of Contents
- [1. User Authentication](#1-user-authentication)
  - [1.1 Registration](#11-registration)
  - [1.2 Login](#12-login)
- [2. Media Upload and Processing](#2-media-upload-and-processing)
  - [2.1 Upload Image](#21-upload-image)
  - [2.2 Upload Video](#22-upload-video)
  - [2.3 Check Processing Status](#23-check-processing-status)
- [3. Query Detection Results](#3-query-detection-results)
  - [3.1 Query by Species](#31-query-by-species)
  - [3.2 Query by Date Range](#32-query-by-date-range)
  - [3.3 Get Detailed Information](#33-get-detailed-information)
  - [3.4 Query Video Frames](#34-query-video-frames)
- [4. Logout](#4-logout)
- [5. Example Responses](#5-example-responses)
- [6. Important Notes](#6-important-notes)

## 1. User Authentication

### 1.1 Registration

1. **Register through Cognito**
   ```bash
   aws cognito-idp sign-up \
       --client-id YOUR_COGNITO_CLIENT_ID \
       --username user@example.com \
       --password "YourPassword123!" \
       --user-attributes \
           Name="email",Value="user@example.com" \
           Name="given_name",Value="John" \
           Name="family_name",Value="Doe"
   ```

2. **Verify Email**
   - Check your email inbox for the verification code
   - Use the code to confirm your registration:
   ```bash
   aws cognito-idp confirm-sign-up \
       --client-id YOUR_COGNITO_CLIENT_ID \
       --username user@example.com \
       --confirmation-code 123456
   ```

### 1.2 Login

1. **Login and Get Tokens**
   ```bash
   aws cognito-idp initiate-auth \
       --client-id YOUR_COGNITO_CLIENT_ID \
       --auth-flow USER_PASSWORD_AUTH \
       --auth-parameters \
           USERNAME=user@example.com,PASSWORD="YourPassword123!"
   ```

2. **Store Access Token**
   ```bash
   # Store the Access Token for API calls
   export ACCESS_TOKEN="eyJraWQiOiJ..."
   ```

## 2. Media Upload and Processing

### 2.1 Upload Image

1. **Get Pre-signed URL**
   ```bash
   curl -X POST \
       -H "Authorization: Bearer $ACCESS_TOKEN" \
       https://your-api-gateway-url/media/upload-url \
       -d '{
           "file_name": "bird_image.jpg",
           "content_type": "image/jpeg"
       }'
   ```

2. **Upload Image**
   ```bash
   curl -X PUT \
       -H "Content-Type: image/jpeg" \
       --data-binary "@bird_image.jpg" \
       "https://your-s3-presigned-url"
   ```

### 2.2 Upload Video

1. **Get Pre-signed URL for Video**
   ```bash
   curl -X POST \
       -H "Authorization: Bearer $ACCESS_TOKEN" \
       https://your-api-gateway-url/media/upload-url \
       -d '{
           "file_name": "bird_video.mp4",
           "content_type": "video/mp4"
       }'
   ```

2. **Upload Video**
   ```bash
   curl -X PUT \
       -H "Content-Type: video/mp4" \
       --data-binary "@bird_video.mp4" \
       "https://your-s3-presigned-url"
   ```

3. **Video Processing Details**
   - Videos are processed frame by frame
   - A preview frame is extracted at 1 second mark
   - Processing time depends on video length and resolution
   - Progress can be monitored through status endpoint

### 2.3 Check Processing Status

```bash
# Check status for any media type (image or video)
curl -X GET \
    -H "Authorization: Bearer $ACCESS_TOKEN" \
    https://your-api-gateway-url/media/status/{media_id}
```

Status Response for Video:
```json
{
  "status": "processing",
  "progress": 45,
  "total_frames": 300,
  "processed_frames": 135,
  "estimated_time_remaining": "2 minutes",
  "preview_frame_url": "https://your-bucket.s3.amazonaws.com/preview/video_123.jpg"
}
```

## 3. Query Detection Results

### 3.1 Query by Species

```bash
# Get all images of a specific bird species
curl -X GET \
    -H "Authorization: Bearer $ACCESS_TOKEN" \
    "https://your-api-gateway-url/media/species/Common%20Kingfisher?limit=10"
```

### 3.2 Query by Date Range

```bash
# Get images from a specific date range
curl -X GET \
    -H "Authorization: Bearer $ACCESS_TOKEN" \
    "https://your-api-gateway-url/media/tags?start_date=2024-03-01&end_date=2024-03-15&limit=10"
```

### 3.3 Get Detailed Information

```bash
# Get detailed information for a specific image
curl -X GET \
    -H "Authorization: Bearer $ACCESS_TOKEN" \
    https://your-api-gateway-url/media/{media_id}
```

### 3.4 Query Video Frames

```bash
# Get detection results for specific frames
curl -X GET \
    -H "Authorization: Bearer $ACCESS_TOKEN" \
    "https://your-api-gateway-url/media/{video_id}/frames?start_frame=0&end_frame=10"
```

## 4. Logout

```bash
# Revoke the access token
aws cognito-idp global-sign-out \
    --access-token $ACCESS_TOKEN

# Clear local token
unset ACCESS_TOKEN
```

## 5. Example Responses

### 5.1 Successful Detection Result
```json
{
  "id": "img-uuid-001",
  "user_id": "user-abc",
  "file_type": "image",
  "s3_path": "species/Common Kingfisher/bird_image.jpg",
  "thumbnail_path": "thumbnail/bird_image.jpg",
  "detected_species": ["Common Kingfisher", "House Sparrow"],
  "detection_boxes": [
    {
      "species": "Common Kingfisher",
      "code": "comkin",
      "box": [0.1, 0.2, 0.3, 0.4],
      "confidence": 0.9234
    }
  ],
  "created_at": "2024-03-15T08:30:45.123Z"
}
```

### 5.2 Video Detection Result
```json
{
  "id": "vid-uuid-001",
  "user_id": "user-abc",
  "file_type": "video",
  "s3_path": "species/Common Kingfisher/bird_video.mp4",
  "thumbnail_path": "preview/bird_video.jpg",
  "detected_species": ["Common Kingfisher", "House Sparrow"],
  "detection_boxes": [
    {
      "species": "Common Kingfisher",
      "code": "comkin",
      "box": [0.1, 0.2, 0.3, 0.4],
      "confidence": 0.9234
    }
  ],
  "detection_frames": [
    {
      "frame_idx": 0,
      "timestamp": 0.0,
      "boxes": [
        {
          "species": "Common Kingfisher",
          "code": "comkin",
          "box": [0.1, 0.2, 0.3, 0.4],
          "confidence": 0.9234
        }
      ]
    },
    {
      "frame_idx": 1,
      "timestamp": 0.033,
      "boxes": []
    }
  ],
  "video_metadata": {
    "duration": 10.5,
    "fps": 30,
    "resolution": "1920x1080",
    "total_frames": 315
  },
  "created_at": "2024-03-15T08:30:45.123Z"
}
```

## 6. Important Notes

### 6.1 System Requirements
- All API endpoints require valid Cognito authentication
- Supported media formats:
  - Images: JPEG, PNG
  - Videos: MP4 (H.264 codec)
- File size limits:
  - Images: 10MB
  - Videos: 100MB
- Processing time:
  - Images: 1-2 minutes
  - Videos: 2-5 minutes per minute of video

### 6.2 Media Processing
- Images:
  - Thumbnails are automatically generated
    - Longest side: 200px
    - Format: JPEG
    - Quality: 75%
  - Original images are preserved
- Videos:
  - Preview frame extracted at 1 second mark
  - Processed at 1 frame per second
  - Detection results stored per frame
  - Original video preserved
  - Preview frame: JPEG, 480p resolution

### 6.3 Detection Results
- Images:
  - Species identification
  - Confidence scores
  - Bounding box coordinates
- Videos:
  - Per-frame detection results
  - Timestamp for each detection
  - Species tracking across frames
  - Confidence scores
  - Bounding box coordinates

### 6.4 Security
- Always use HTTPS for API calls
- Keep your access token secure
- Log out when finished
- Do not share your credentials

### 6.5 Best Practices
- Use descriptive filenames
- Check processing status before querying results
- Use pagination for large result sets
- Monitor your API usage
- For videos:
  - Use H.264 codec for best compatibility
  - Keep videos under 5 minutes for faster processing
  - Consider video resolution (1080p recommended)
  - Check frame rate (30fps recommended)

---

For additional support or to report issues, please contact the system administrator or refer to the main project documentation. 