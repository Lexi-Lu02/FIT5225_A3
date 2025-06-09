# BirdTagMedia DynamoDB Table Schema (Professional English Version)

This document describes the unified DynamoDB table schema for all media types (image, audio, video) in the Assignment project, including field definitions, types, descriptions, and sample records.

---

## Table Fields

| Field Name           | Type           | Description                                              | Applicable Media |
|----------------------|----------------|----------------------------------------------------------|------------------|
| id                   | string (PK)    | Primary key, unique ID (UUID)                            | all              |
| user_id              | string         | Uploader's user ID (from Cognito, or None if unavailable)| all              |
| file_type            | string         | Media type: 'image', 'audio', or 'video'                 | all              |
| s3_path              | string         | S3 path of the original file                             | all              |
| thumbnail_path       | string         | S3 path of the thumbnail (image/video), None for audio   | image, video     |
| detected_species     | list<string>   | Array of detected bird species names                     | all              |
| detection_boxes      | list<map>      | Detection boxes (YOLO output for image/video)            | image, video     |
| detection_segments   | list<map>      | Detection segments (BirdNET output for audio)            | audio            |
| detection_frames     | list<map>      | Detection frames (YOLO output for video)                 | video            |
| created_at           | string         | Upload/analysis timestamp (ISO8601 string)               | all              |

---

## Field Details

- **id**: Unique primary key, UUID format
- **user_id**: Uploader's user ID, from Cognito (or None if not available)
- **file_type**: Media type, one of 'image', 'audio', or 'video'
- **s3_path**: S3 path of the original media file
- **thumbnail_path**: S3 path of the thumbnail; present for images/videos, None for audio
- **detected_species**: All bird species detected in this media (array of species names)
- **detection_boxes** (image/video): Object detection boxes, each with:
  - species: Species name (string)
  - code: Species code (string)
  - box: [x_min, y_min, x_max, y_max] (float array, normalized coordinates)
  - confidence: Confidence score (float, 0-1)
- **detection_segments** (audio): BirdNET output segments, each with:
  - species: Species name (string)
  - code: Species code (string)
  - start: Segment start time (float, seconds)
  - end: Segment end time (float, seconds)
  - confidence: Confidence score (float, 0-1)
- **detection_frames** (video): Detection results per frame, each with:
  - frame_idx: Frame index (int)
  - boxes: list<map>, each map as in detection_boxes
- **created_at**: Record creation time, ISO8601 format

---

## Sample Records

### 1. Image Record
```json
{
  "id": "img-uuid-001",
  "user_id": "user-abc",
  "file_type": "image",
  "s3_path": "upload/image/bird1.jpg",
  "thumbnail_path": "thumbnail/image/bird1_thumb.jpg",
  "detected_species": ["Eurasian Magpie", "Blue Jay"],
  "detection_boxes": [
    {
      "species": "Eurasian Magpie",
      "code": "eurmag",
      "box": [0.12, 0.15, 0.45, 0.40],
      "confidence": 0.91
    },
    {
      "species": "Blue Jay",
      "code": "blujay",
      "box": [0.50, 0.20, 0.80, 0.55],
      "confidence": 0.87
    }
  ],
  "detection_segments": null,
  "detection_frames": null,
  "created_at": "2024-06-01T12:00:00Z"
}
```

### 2. Audio Record
```json
{
  "id": "aud-uuid-002",
  "user_id": "user-def",
  "file_type": "audio",
  "s3_path": "species/Black-capped Chickadee/test_audio.wav",
  "thumbnail_path": null,
  "detected_species": ["Black-capped Chickadee", "House Finch", "Blue Jay"],
  "detection_boxes": null,
  "detection_segments": [
    {
      "species": "Black-capped Chickadee",
      "code": "bkcchi",
      "start": 0.0,
      "end": 3.0,
      "confidence": 0.8141
    },
    {
      "species": "House Finch",
      "code": "houfin",
      "start": 9.0,
      "end": 12.0,
      "confidence": 0.6394
    }
    // ... more segments ...
  ],
  "detection_frames": null,
  "created_at": "2024-06-01T12:34:56.789Z"
}
```

### 3. Video Record
```json
{
  "id": "vid-uuid-003",
  "user_id": "user-xyz",
  "file_type": "video",
  "s3_path": "upload/video/bird2.mp4",
  "thumbnail_path": "thumbnail/video/bird2_thumb.jpg",
  "detected_species": ["Blue Jay"],
  "detection_boxes": [
    {
      "species": "Blue Jay",
      "code": "blujay",
      "box": [0.10, 0.12, 0.30, 0.35],
      "confidence": 0.92
    }
  ],
  "detection_segments": null,
  "detection_frames": [
    {
      "frame_idx": 0,
      "boxes": [
        {
          "species": "Blue Jay",
          "code": "blujay",
          "box": [0.10, 0.12, 0.30, 0.35],
          "confidence": 0.92
        }
      ]
    },
    {
      "frame_idx": 1,
      "boxes": []
    }
    // ... more frames ...
  ],
  "created_at": "2024-06-01T13:00:00Z"
}
```

---

## Notes
- This schema is compatible with the recommended Assignment design and supports unified storage for images, audio, and video.
- Fields not applicable to a media type should be set to null or omitted.
- The structure of detection segments, boxes, and frames facilitates frontend visualization, querying, and analytics.
- It is recommended to integrate user_id with Cognito for traceability and access control. 
