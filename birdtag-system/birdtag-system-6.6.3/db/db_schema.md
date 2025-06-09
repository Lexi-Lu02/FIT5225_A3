# BirdTagMedia DynamoDB 表结构说明（Assignment全媒体通用）

本文件描述了Assignment项目中所有媒体类型（图片、音频、视频）统一的DynamoDB表（BirdTagMedia）字段结构、类型、含义及样例。

---

## 表结构字段

| 字段名              | 类型         | 说明                                      | 适用类型      |
|---------------------|-------------|-------------------------------------------|---------------|
| id                  | string (PK) | 主键，唯一ID（UUID）                      | all           |
| user_id             | string      | 上传用户ID（Cognito，若无则为None）       | all           |
| file_type           | string      | 文件类型（image/audio/video）             | all           |
| s3_path             | string      | 原文件S3路径                              | all           |
| thumbnail_path      | string      | 缩略图S3路径（图片/视频有，音频为空）     | image,video   |
| detected_species    | list<string>| 检测到的物种（物种名数组）                | all           |
| detection_boxes     | list<map>   | 检测框（图片/视频，YOLO输出）             | image,video   |
| detection_segments  | list<map>   | 检测片段（音频，BirdNET输出）             | audio         |
| detection_frames    | list<map>   | 检测帧（视频，YOLO输出）                  | video         |
| created_at          | string      | 上传/分析时间（ISO8601字符串）            | all           |

---

## 字段详细说明

- **id**：唯一主键，UUID格式
- **user_id**：上传用户ID，来自Cognito（如无则为None）
- **file_type**：文件类型，'image'/'audio'/'video'
- **s3_path**：原始文件在S3中的路径
- **thumbnail_path**：缩略图S3路径，图片/视频有，音频为None
- **detected_species**：本媒体检测到的所有鸟类物种名称
- **detection_boxes**（图片/视频）：目标检测框，结构如下：
  - species: 物种名称（string）
  - code: 物种代码（string）
  - box: [x_min, y_min, x_max, y_max]（float数组，归一化坐标）
  - confidence: 置信度（float, 0-1）
- **detection_segments**（音频）：BirdNET输出的每个检测片段，结构如下：
  - species: 物种名称（string）
  - code: 物种代码（string）
  - start: 检测片段起始时间（float, 秒）
  - end: 检测片段结束时间（float, 秒）
  - confidence: 置信度（float, 0-1）
- **detection_frames**（视频）：每帧检测结果，结构如下：
  - frame_idx: 帧编号（int）
  - boxes: list<map>，每个map结构同detection_boxes
- **created_at**：记录创建时间，ISO8601格式

---

## 样例

### 1. 图片记录
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

### 2. 音频记录
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
    // ... 其余片段 ...
  ],
  "detection_frames": null,
  "created_at": "2024-06-01T12:34:56.789Z"
}
```

### 3. 视频记录
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
    // ... 其余帧 ...
  ],
  "created_at": "2024-06-01T13:00:00Z"
}
```

---

## 说明
- 该表结构兼容Assignment推荐设计，支持图片、音频、视频三类媒体统一存储。
- 各字段仅在适用类型下有值，其他类型可为null或不写入。
- 检测片段、检测框、检测帧等结构便于后续前端可视化、查询和统计。
- user_id建议与Cognito集成，便于用户溯源和权限控制。 