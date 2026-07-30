# 照片 API 三端点与草稿集成（MinIO）

## Description

将照片处理器接入 Resume Builder API：上传处理、确认采用、移除三个端点。原图与处理结果分别持久化 MinIO（可追溯），仅在用户 confirm 后才写入草稿 `identity.photo`，避免未确认照片进入导出。

PRD Reference: tasks/prd-resume-toolchain-increments.md US-002 / FR-4, FR-5, FR-8
SPEC Reference: specs/RIP-004-resume-builder/spec.md「API 设计」「错误分类」

## Acceptance Criteria

- [x] `POST /api/v1/resume-builder/{draft_id}/photo`：multipart 上传，query `bg_color`（默认 white）；返回原图/结果 presigned URL + 处理元信息（`background_replaced` / `degraded_reason`）
- [x] 非 jpg/png 或 >10MB → HTTP 400 `INVALID_PHOTO`；无人脸 → HTTP 422 `FACE_NOT_FOUND`；imaging 依赖未安装 → HTTP 501 `IMAGING_NOT_AVAILABLE`
- [x] 原图与结果分别写 MinIO：`photos/{draft_id}/original-*.jpg` / `processed-*.png`
- [x] `PUT /{draft_id}/photo/confirm`：校验对象属于该草稿（否则 400 `PHOTO_NOT_OWNED`）→ 写入 `identity.photo`
- [x] `DELETE /{draft_id}/photo`：清除字段，MinIO 对象保留
- [x] 单测覆盖上传/确认/删除/400/422/501 六路径（mock MinIO + processor）
- [x] Lint / mypy 通过

> Shipped: PR #12（squash 入 main c0a55f8）

## Dependencies

Issue #32

## Type

backend

## Priority

high
