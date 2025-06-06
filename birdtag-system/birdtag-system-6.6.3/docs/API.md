# BirdTag API Documentation

## Authentication
All API endpoints require authentication using AWS Cognito. Include the JWT token in the Authorization header:
```
Authorization: Bearer <token>
```

## Endpoints

### Upload
- **GET /upload/presign**
  - Get a presigned URL for uploading files
  - Query Parameters:
    - fileType: MIME type of the file
    - fileName: Name of the file
  - Returns:
    - uploadUrl: Presigned URL for upload
    - fileKey: Key to use for the file

### Search
- **POST /v1/search**
  - Search for media files
  - Body:
    ```json
    {
      "query": "string",
      "tags": ["string"],
      "startDate": "YYYY-MM-DD",
      "endDate": "YYYY-MM-DD"
    }
    ```
  - Returns:
    ```json
    {
      "results": [
        {
          "fileKey": "string",
          "tags": ["string"],
          "uploadDate": "string",
          "url": "string"
        }
      ]
    }
    ```

### Tags
- **POST /v1/tags/update**
  - Update tags for a file
  - Body:
    ```json
    {
      "fileKey": "string",
      "tags": ["string"]
    }
    ```
  - Returns:
    ```json
    {
      "message": "string"
    }
    ```

### Bird Detection
- **POST /v1/detect**
  - Detect birds in an image
  - Body:
    ```json
    {
      "fileKey": "string"
    }
    ```
  - Returns:
    ```json
    {
      "detections": [
        {
          "species": "string",
          "confidence": number,
          "bbox": [number, number, number, number]
        }
      ]
    }
    ```

### BirdNET Analysis
- **POST /v1/analyze**
  - Analyze bird sounds in an audio file
  - Body:
    ```json
    {
      "fileKey": "string"
    }
    ```
  - Returns:
    ```json
    {
      "results": [
        {
          "species": "string",
          "confidence": number,
          "timestamp": number
        }
      ]
    }
    ``` 