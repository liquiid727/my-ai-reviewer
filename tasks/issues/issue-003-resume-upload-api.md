# Resume File Upload API + MinIO Storage

## Description

实现简历文件上传 API，支持 PDF/DOCX/TXT/MD 格式校验和大小限制，上传至 MinIO 对象存储，计算文件 hash 防重复，创建 resume + file 记录。

PRD Reference: US-002
SPEC Reference: Section 4.1, 4.2, 5.1

## Acceptance Criteria

- [ ] `POST /api/v1/resume/upload` 接收 multipart/form-data
- [ ] 文件格式校验：仅允许 `.pdf`, `.docx`, `.txt`, `.md`，其他格式返回 `{"code": 1001, "message": "Unsupported file format"}`
- [ ] 文件大小限制 10MB，超限返回 `{"code": 1001, "message": "File too large"}`
- [ ] 计算文件 SHA256 hash
- [ ] 相同 hash 文件重复上传 → 返回已有 resume_id（code: 0，不报错）
- [ ] 新文件上传至 MinIO `resumes` bucket，路径：`{user_id}/{uuid}.{ext}`
- [ ] 创建 `files` 记录（original_name, storage_path, content_type, size_bytes, sha256_hash）
- [ ] 创建 `resumes` 记录（status: "uploaded", file_id 关联）
- [ ] `backend/infrastructure/storage/minio_client.py` 封装 MinIO 上传/下载
- [ ] 响应格式：`{"code": 0, "message": "success", "data": {"resume_id": "...", "file_id": "...", "status": "uploaded"}}`
- [ ] `backend/api/v1/resume.py` 路由 + `backend/api/v1/schemas.py` 请求/响应模型
- [ ] `backend/application/resume_service.py` 编排上传逻辑
- [ ] `backend/domain/resume/exceptions.py` 定义 UnsupportedFileFormatError, FileTooLargeError, DuplicateResumeError
- [ ] Typecheck 通过

## Dependencies

Issue #2

## Type

backend

## Priority

P0
