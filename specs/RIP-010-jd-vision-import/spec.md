# RIP-010 JD Vision Import

## 1. Meta

- **Spec ID:** RIP-010
- **Title:** JD Vision Import
- **Epic:** Resume Intelligence Platform
- **Status:** Proposed
- **Owner Agent:** Backend Agent + Frontend Agent
- **Depends On:** RIP-007
- **Prerequisites:** ready JD aggregate, MinIO file storage, Celery run-id guard, verified database LLM configuration, existing text `JDExtractor`
- **PRD:** `spec-draft/jd-intelligence-v2-2026-08-05.md` (US-001~US-004; FR-1~FR-10, FR-25, FR-28~FR-30)
- **Baseline:** `main` at `8c05329`; generated 2026-08-05 from a dirty worktree without modifying existing application code

## 2. Goal

允许用户在 JD Library 上传一张或多张岗位截图，由明确支持 Vision 的已验证 LLM 转写图片文字，然后复用 RIP-007 的规范化、重复检测、文本 JD 结构化、人工编辑和恢复流程。

## 3. Why This Exists

当前 `/jd/import/file` 只接受 PDF、DOCX、TXT、Markdown；图片会在 API 层被拒绝，扫描 PDF 也没有视觉识别回退。现有 `LLMGateway.complete()` 虽接受宽泛 message 字典，但没有统一图片内容类型、provider capability 或跨 provider 的多模态转换测试，不能视作已经支持 Vision。

本 SPEC 将“图片转文字”和“文字转结构化 JD”明确分成两阶段。这样可以复用现有 JDExtractor、重复检测和人工修正，并保留转写证据、模型版本和失败边界。

## 4. Out of Scope

- 本地 OCR/Tesseract/PaddleOCR 不是首版主链路。
- GIF、SVG、TIFF、HEIC、视频和任意压缩包不受支持。
- 扫描 PDF Vision 回退默认关闭；待纯图片链路验收后作为兼容增量开启。
- 不修改 `rules_v1` 或新增 JD/简历匹配逻辑。
- 不实现认证、多租户或外部招聘系统同步。
- 不声称文本 `PrivacyGuard` 可以检查图片像素中的个人信息。

## 5. Deliverables

- LLM capability 持久化、验证与设置页展示。
- provider-neutral 多模态消息类型及 OpenAI/Anthropic adapter 转换。
- `POST /api/v1/jd/import/images` 多图片异步导入。
- `jd_source_assets` 有序资源表及 `job_descriptions` Vision 元数据。
- Vision 转写、文本质量检查、重复检测、现有 JDExtractor 结构化处理。
- 图片导入 UI、处理状态、失败恢复和安全披露。
- 单元、迁移、API、worker、隐私日志和浏览器验收证据。

## 6. Domain

### 6.1 Source and State

```text
JDSourceType += image
JDProcessingStep += source_validate | vision_extract | text_quality_check

create
  -> processing/source_validate
  -> processing/vision_extract
  -> processing/text_quality_check
  -> processing/duplicate_check
  -> duplicate_pending OR processing/llm_extract
  -> ready/done OR failed/<failed_step>
```

每次导入、retry 或 reextract 生成新的 `processing_run_id`。只有持有当前 run id 的 worker 可以更新 JD、asset 转写状态或最终结构化字段。

### 6.2 Validation Rules

| Rule | Limit |
|---|---:|
| Formats | PNG, JPG/JPEG, WEBP |
| Image count | 1~8 |
| Per-image encoded size | <= 10MB |
| Total encoded size | <= 30MB |
| Decoded pixels | <= 25MP/image |
| Maximum edge | <= 4000px after safe normalization |
| Extracted visible text | 30~100000 characters |

扩展名、声明 MIME、magic bytes 和实际解码格式必须一致。EXIF 在持久化前移除；解码器必须阻止 decompression bomb。图片顺序由 multipart 顺序固定，任何客户端文件名都只作为显示元数据。

### 6.3 Vision Transcription Contract

转写输出必须通过 Pydantic 校验：

```json
{
  "pages": [
    {
      "asset_id": "uuid",
      "order": 0,
      "text": "职位描述……",
      "warnings": []
    }
  ]
}
```

- Vision 任务只做忠实转写，不直接决定 required skills 或职位结论。
- 页面顺序拼接为 `raw_text`，同时保留页/asset 映射。
- 无文字、明显截断、未知 asset ID 或 schema 非法时失败；schema 修正最多重试一次。
- 转写完成后调用现有 `JDExtractor.extract(raw_text)`，输出仍为统一 `JDExtraction`。

### 6.4 Capability Contract

```text
LLMCapabilities:
  supports_text: bool
  supports_structured_output: bool
  supports_vision: bool
  max_images: int | null
  max_image_bytes: int | null
  transport: openai_chat | anthropic_messages | none
  verified_at: datetime | null
```

能力来自显式配置及验证结果；严禁通过模型名、provider 名或 base URL 猜测。`complete_multimodal()` 接受 domain-neutral text/image blocks，provider-specific payload 只能在 infrastructure adapter 内构建。

## 7. Application

### 7.1 Import Flow

```text
JD image import API
  -> validate count/encoded size/magic bytes/decode/pixels
  -> strip EXIF and upload ordered assets to MinIO
  -> persist JD + assets + current run
  -> dispatch source_validate
  -> vision_extract via active verified config
  -> text_quality_check and persist raw_text/page map
  -> existing duplicate_check
  -> existing JDExtractor text extraction
  -> ready/done
```

外部 LLM 调用不得持有数据库事务。上传或落库部分失败时执行补偿删除；任务终态或用户删除时按保留策略删除原图。默认保留原图用于人工复核，直到 JD 删除；生产策略可缩短 TTL，但不得留下无主对象。

### 7.2 Retry and Failure

- `source_validate` 的确定性输入错误不可重试。
- Vision timeout、429 和临时 provider/network 错误最多自动重试 2 次，指数退避并带 jitter。
- Vision schema 错误只做一次模型自我修正，不与 transport retry 相乘形成无界调用。
- `retry` 从失败步骤开始，但必须生成新 run id。
- `reextract` 可复用已有安全图片对象；对象已过期时返回不可重试的资源过期错误。

### 7.3 Privacy and Disclosure

图片会发送给用户主动配置的外部 Vision provider。提交前 UI 必须明确披露这一点。系统不把图片 base64、完整转写、prompt、provider 原始错误或 API key 写入日志。转写文本进入结构化抽取前可运行文本级安全检查，但不得把它描述为对发送前图片像素的保护。

## 8. Repository

建议实现位置：

```text
backend/domain/llm/multimodal.py                 [NEW: provider-neutral blocks/capabilities]
backend/domain/jd/schemas.py                     [MODIFY: image requests/status/page mapping]
backend/application/jd_import_service.py         [MODIFY: ordered image import]
backend/application/jd_service/processing.py     [MODIFY: vision/text-quality steps]
backend/infrastructure/llm/gateway.py             [MODIFY: complete_multimodal]
backend/infrastructure/llm/providers/*.py         [MODIFY: provider conversion]
backend/infrastructure/db/models.py               [MODIFY]
backend/tasks/jd_tasks.py                         [MODIFY: guarded Vision stages]
frontend/src/api/jd.ts                            [MODIFY]
frontend/src/components/jd/JDImportDialog.tsx     [MODIFY]
frontend/src/pages/JDDetailPage.tsx               [MODIFY]
infra/alembic/versions/<revision>_jd_vision.py     [NEW]
```

API 继续调用 application；domain 不依赖 SDK/ORM；Celery task 只负责边界、retry 和状态推进。

## 9. API

### 9.1 Endpoint

```http
POST /api/v1/jd/import/images
Content-Type: multipart/form-data

images: repeated UploadFile (1..8)
title: optional string
company: optional string
allow_duplicate: optional boolean=false
acknowledge_external_vision: boolean=true
```

成功返回统一 `APIResponse`，`data` 至少包含 `id/status/processing_step/processing_run_id`。旧 `/jd/import/file` 不改变允许格式或响应。

`GET /api/v1/jd/{id}` 增量返回：

```json
{
  "source_type": "image",
  "processing_step": "vision_extract",
  "source_assets": [{"id":"uuid","order":0,"media_type":"image/png","status":"ready"}],
  "vision": {"provider":"openai","model":"configured-model","transcriber_version":"jd-vision-v1","warnings":[]}
}
```

不得返回对象密钥、signed URL、base64 或 provider 请求体。

### 9.2 Error Mapping

| Public code | Internal key | Condition | Retryable |
|---:|---|---|---|
| 1001 | `JD_IMAGE_INVALID` | 类型、数量、大小、像素、损坏或未确认披露 | no |
| 1002 | `JD_IMAGE_SOURCE_MISSING` | JD 或原图不存在/已过期 | no |
| 1003 | `JD_IMAGE_STATE_CONFLICT` | 状态或 run 冲突 | after refresh |
| 428 | `JD_VISION_NOT_CONFIGURED` | 无已验证 Vision 配置 | after config |
| 5001 | `JD_VISION_FAILED` | Vision/结构化输出最终失败 | yes |
| 5003 | `JD_IMAGE_STORAGE_FAILED` | 对象存储读写失败 | depends on cause |
| 5004 | `JD_IMAGE_DISPATCH_FAILED` | broker 派发失败 | yes |

## 10. Database Impact

新增 `jd_source_assets`：

| Column | Type | Notes |
|---|---|---|
| id | UUID PK | asset identity |
| jd_id | UUID FK | `ON DELETE CASCADE` |
| file_id | UUID FK files | `ON DELETE SET NULL` |
| order_index | int | unique per JD |
| media_type | varchar(50) | decoded type |
| byte_size | bigint | encoded bytes |
| width/height | int | decoded dimensions |
| content_hash | char(64) | sanitized image hash |
| status | varchar(30) | stored/transcribing/ready/failed/deleted |
| transcript_blocks | JSONB | bounded page text mapping |
| processing_error_code | varchar(80) | safe internal key |
| created_at/updated_at | timestamptz | audit |

`job_descriptions`：扩展 `source_type` check 为 `text/file/url/image`；扩展 processing step；新增 `vision_metadata JSONB` 和可空 `source_asset_count`。`llm_configs` 新增 `capabilities JSONB NOT NULL DEFAULT '{}'` 与 `capabilities_verified_at`。

迁移必须回填现有配置为空能力并保持 text-only 可用；空能力不得被解释为支持 Vision。Downgrade 仅在不存在 image JD/asset 时允许，或明确拒绝以防数据丢失。

## 11. Test Plan

- Unit：MIME/magic/decode/pixel/数量/大小限制，EXIF 清除，capability 判定，多模态 provider payload，schema 修正和安全日志。
- Migration：upgrade、历史配置回填、约束、索引、downgrade guard。
- API：成功、空文件、伪装扩展名、损坏、超限、未确认披露、无 Vision 配置、broker/storage 失败。
- Worker：正常转写、无文字、非法 asset ID、超时/429/重试、stale run no-op、删除后晚到任务。
- Regression：text/file/url、legacy `POST /jd`、重复确认、人工 edit/reextract。
- Frontend：validation、processing/ready/failed/retry、轮询终止、中英文。
- Browser：桌面/移动端上传成功、错误、重试和返回详情；使用合成 JD 图片。

## 12. Definition of Done

- [ ] US-001~US-004 和 FR-1~FR-10、FR-25、FR-28~FR-30 均映射到自动化或浏览器证据。
- [ ] 图片只会发送给显式已验证的 Vision 配置。
- [ ] Vision 转写复用现有 JDExtractor，没有第二套结构化 JD schema。
- [ ] 日志、错误、任务元数据和响应不含图片 base64、prompt、完整转写或密钥。
- [ ] 旧 JD 导入、编辑、重复检测和 `rules_v1` 匹配回归通过。
- [ ] Alembic、相关 Ruff/mypy/pytest、frontend lint/build/component tests 和浏览器验收已记录真实结果。
- [ ] tasks、roadmap、current、design/database/backend/frontend 文档按 as-built 更新。
