# FIT5225 Assignment 3 - API endpoints and configuration alignment documentation

This file is used to unify and share all key API paths, request/response formats, environment variables, and external dependency URLs within the team.
Please fill in the `<To be filled>` part according to the table and example below to ensure consistency across modules and environments.

---

## 1. 环境与基础配置

| 配置项                     | 变量名                 | 开发环境（Dev）         |
|----------------------------|------------------------|-------------------------|--------------------------|------------------------|
| API 基础 URL               | `BASE_URL`             | `https://dev.<域名>`    |
| AWS 区域                   | `AWS_REGION`           | `<待填写>`              |
| Cognito User Pool ID       | `COGNITO_USER_POOL_ID` | `<待填写>`              |
| Cognito App Client ID      | `COGNITO_CLIENT_ID`     | `<待填写>`              |
| DynamoDB 表名              | `DDB_TABLE_NAME`        | `BirdTagMetadataDev`    |
| S3 上传桶（原图）          | `S3_UPLOAD_BUCKET`      | `birdtag-uploads-dev`   |
| S3 缩略图桶                | `S3_THUMBNAIL_BUCKET`   | `birdtag-thumbs-dev`    |
| SNS 通知主题前缀           | `SNS_TOPIC_PREFIX`      | `birdtag-notify-dev`    |
| OpenAPI 文档 URL           | —                       | `<待填写 swagger.json>` |

---

## 2. 认证 & 授权（Cognito + JWT）

| 功能        | 方法  | 路径                           | 请求头                | 请求体示例                                                                                 | 响应体示例                                                                                         |
|-------------|-------|--------------------------------|-----------------------|--------------------------------------------------------------------------------------------|----------------------------------------------------------------------------------------------------|
| 用户注册    | POST  | `/auth/signup`                 | `Content-Type: application/json`<br>`Accept: application/json` | ```json<br>{<br>  "email": "<待填写>",<br>  "password": "<待填写>",<br>  "given_name": "",<br>  "family_name": ""<br>}``` | ```json<br>{<br>  "userSub": "<UUID>",<br>  "message": "Verification code sent"<br>}```               |
| 确认注册    | POST  | `/auth/confirm-signup`         | 同上                  | ```json<br>{<br>  "email": "<待填写>",<br>  "code": "<验证码>"<br>}```                        | ```json<br>{<br>  "message": "User confirmed"<br>}```                                                |
| 用户登录    | POST  | `/auth/login`                  | 同上                  | ```json<br>{<br>  "email": "<待填写>",<br>  "password": "<待填写>"<br>}```                    | ```json<br>{<br>  "id_token": "<JWT>",<br>  "access_token": "<JWT>",<br>  "refresh_token": "<JWT>"<br>}``` |
| 刷新 Tokens | POST  | `/auth/refresh`                | 同上                  | ```json<br>{<br>  "refresh_token": "<JWT>"<br>}```                                           | 同登录                                                                                             |
| 用户登出    | POST  | `/auth/logout`                 | `Authorization: Bearer <access_token>` | _无_                                                                                     | ```json<br>{<br>  "message": "Logged out"<br>}```                                                   |
| 获取用户信息| GET   | `/auth/me`                     | `Authorization: Bearer <access_token>` | _无_                                                                                     | ```json<br>{<br>  "email": "",<br>  "given_name": "",<br>  "family_name": ""<br>}```                 |

---

## 3. 文件上传 (Upload)

| 功能                  | 方法  | 路径                                  | 请求头                         | 请求体/参数                                                                                                                  | 响应体                                                                                                  |
|-----------------------|-------|---------------------------------------|--------------------------------|-----------------------------------------------------------------------------------------------------------------------------|---------------------------------------------------------------------------------------------------------|
| 生成预签名上传 URL    | GET   | `/upload/presign?filename={fileName}` | `Authorization: Bearer <token>` | Query String: `filename=<原始文件名>`                                                                                         | ```json<br>{<br>  "uploadUrl": "<S3 PUT URL>",<br>  "fileKey": "<S3 Object Key>"<br>}```                   |
| 客户端上传（PUT）     | PUT   | `<uploadUrl>`                         | `Content-Type: <MIME>`          | binary data                                                                                                                 | HTTP 200 / 204                                                                                         |

> After the client uploads, the ObjectCreated event of the S3 bucket will trigger the **thumbnail generation** and **automatic labeling** Lambda functions without the need for additional calls.

---

## 4. 查询与检索 (Search & Resolve)

| 功能                | 方法  | 路径                    | 请求头                         | 请求体示例                                                                                           | 响应体示例                                                                              |
|---------------------|-------|-------------------------|--------------------------------|------------------------------------------------------------------------------------------------------|-----------------------------------------------------------------------------------------|
| 按标签 & 数量查询   | POST  | `/v1/search`            | `Authorization: Bearer <token>` | ```json<br>{<br>  "crow": 2,<br>  "pigeon": 1<br>}```                                                 | ```json<br>{<br>  "results": [<br>    { "fileKey": "", "thumbnailUrl": "", "tags": [] }<br>  ]<br>}``` |
| 仅按物种查询        | POST  | `/v1/search`            | 同上                           | ```json<br>{ "crow": 1 }```                                                                           | 同上                                                                                     |
| 缩略图反查原图      | POST  | `/v1/resolve`           | 同上                           | ```json<br>{ "thumbnailUrl": "<S3 缩略图 URL>" }```                                                  | ```json<br>{ "originalUrl": "<S3 原图 URL>" }```                                          |
| 文件上传检索        | POST  | `/v1/search-by-file`    | 同上 + `Content-Type: multipart/form-data` | Form Data: `file`=binary 图片/音频/视频                                                              | 同 `/v1/search`                                                                           |

---

## 5. 手动标签管理 & 删除 (Tags & Deletion)

| 功能                  | 方法  | 路径                    | 请求头                         | 请求体示例                                                                                                  | 响应体示例                                                               |
|-----------------------|-------|-------------------------|--------------------------------|-------------------------------------------------------------------------------------------------------------|--------------------------------------------------------------------------|
| 批量增删标签          | POST  | `/v1/tags/update`       | `Authorization: Bearer <token>` | ```json<br>{<br>  "fileKeys": ["<key1>","<key2>"],<br>  "operation": 1,      // 1=添加，0=删除<br>  "tags": ["crow,2","pigeon,1"]<br>}``` | ```json<br>{<br>  "updated": true<br>}```                                 |
| 删除文件及元数据      | POST  | `/v1/files/delete`      | 同上                           | ```json<br>{<br>  "fileKeys": ["<key1>","<key2>"]<br>}```                                                       | ```json<br>{<br>  "deleted": true<br>}```                                 |

---

## 6. 通知订阅 (Notifications)

| 功能              | 方法  | 路径                   | 请求头                         | 请求体示例                                              | 响应体示例                                |
|-------------------|-------|------------------------|--------------------------------|---------------------------------------------------------|-------------------------------------------|
| 订阅标签通知      | POST  | `/v1/subscribe`        | `Authorization: Bearer <token>` | ```json<br>{ "email": "<待填写>", "species": "<crow>" }``` | ```json<br>{ "subscribed": true }```      |
| 取消订阅          | POST  | `/v1/unsubscribe`      | 同上                           | ```json<br>{ "email": "<待填写>", "species": "<crow>" }``` | ```json<br>{ "unsubscribed": true }```    |

---

## 7. 错误码 & 响应格式

| HTTP 状态码 | 含义                             | 响应体示例                                                   |
|-------------|----------------------------------|--------------------------------------------------------------|
| 200         | 成功                             | `{ "message": "...", ... }`                                  |
| 400         | 参数校验失败                     | `{ "error": "BadRequest", "message": "<xxx>" }`         |
| 401         | 未授权 / Token 无效              | `{ "error": "Unauthorized", "message": "xxxx" }` |
| 403         | 拒绝访问                         | `{ "error": "Forbidden", "message": "<xxx>" }`     |
| 404         | 资源不存在                       | `{ "error": "NotFound", "message": "<xxx>" }`     |
| 500         | 服务器内部错误                   | `{ "error": "InternalError", "message": "<xxxx>" }`    |

---

## 8. 版本管理 & 路径规范

- **API version number**: All official interface prefixes use `/v1/` (such as `/v1/search`).
- **Resource naming**:
- URLs all use lowercase letters and hyphens (`-`), and do not use underscores or camel case.
- Do not add `/` at the end of the path unless necessary.
- **Parameter naming**:
- JSON fields use camel case (`fileKeys`, `thumbnailUrl`);
- Query parameters use lowercase and hyphens (`?file-key=`).

---

## 9. 参考文档 & 链接

- OpenAPI documentation (Swagger UI): `<URL to be filled in>`
- API flow chart (Draw.io / Lucidchart): `<Link to be filled in>`
- IAM & Cognito configuration guide: `<Document link to be filled in>`
- Team communication (Slack/Teams): `<Group link to be filled in>`