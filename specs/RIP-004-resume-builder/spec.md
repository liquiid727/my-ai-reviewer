# RIP-004 — Resume Builder（制作 / 润色 / 照片美化）

**Version**: v1.1
**Status**: Partially Implemented（草稿/模板/润色/评分/导出已实现；照片美化未实现）
**Estimated**: 剩余 3-4 天（照片美化）
**Track**: Resume Builder（PRD `docs/prd/resume-builder.md`）
**Source**: `tasks/prd-resume-toolchain-increments.md`（US-001~004 / FR-1~8, FR-14）；方向文档 `docs/prd/resume-builder.md` §3.5

---

## 目标

在 Resume Intelligence 数据底座（解析 → Facts → Profile）之上，提供候选人侧的简历制作闭环：**从 Profile 生成草稿 → 编辑 / AI 润色 → 照片美化 → 模板渲染 → 评分 → 导出 PDF**。本 spec 对既有实现做追溯性记录，并给出本期增量「图片（证件照）美化」的技术设计。

## 现状

已实现（代码先行，本 spec 补记）：

- `domain/resume_builder/schemas.py`：`ResumeDraft` / `DraftSection` / `DraftItem` / `DesignTokens` / `PolishRequest` / `ExportOptions`
- `domain/resume_builder/services.py`：`profile_to_draft`、草稿 CRUD、`polish_draft_section`、`score_draft`
- `infrastructure/polishers/llm_polisher.py`：`LLMResumePolisher`（保留原文、逐条建议）
- `infrastructure/rendering/`：`HtmlRenderer`（Jinja2 三模板）+ `PdfRenderer`（Playwright 打印 A4；分页能力由 RIP-005 接管）
- `api/v1/resume_builder.py`：`/templates`、`/from-resume/{id}`、GET/PUT `/{draft_id}`、`/polish`、`/score`、`/preview`、`/export`
- DB：`ResumeDraftModel` / `ResumeExportModel`（迁移 `d4e5f6a7b8c9`）
- 前端：`frontend/src/pages/BuilderPage.tsx`
- 单测：`test_resume_builder_services.py`、`test_polisher.py`、`test_html_renderer.py`、`test_one_page_logic.py`

缺失（本期增量，详见下文设计）：照片上传 / 人脸裁剪 / 背景替换 / 画质增强 / 模板头像渲染。

---

# 增量设计：图片（证件照）美化

## 设计决策

| 决策 | 选择 | 理由 |
|---|---|---|
| 处理位置 | 全本地（Pillow + OpenCV + rembg） | FR-14 照片不出网；LLM 网关不接收图片 |
| 人脸检测 | OpenCV Haar cascade | 免模型下载、CPU 快、证件照场景足够 |
| 依赖管理 | pyproject 可选分组 `imaging` | opencv+rembg+onnxruntime 体积大；未安装时 API 返回 501 |
| 照片持久化 | MinIO 对象，不新增 DB 表 | 草稿 `content` 为 JSONB，`identity.photo` 存对象名即可；原图/结果对象保留可追溯 |
| 确认语义 | 两段式：处理返回预览 → confirm 写入草稿 | FR-5；避免用户未确认的照片进入导出 |
| PDF 照片 | data URI 内联 | FR-7；Playwright 打印无外链依赖，离线可导出 |

## 组件与文件

```
backend/
├── infrastructure/imaging/            [NEW]
│   ├── __init__.py
│   ├── exceptions.py                  # FaceNotFoundError / ImageDecodeError
│   └── photo_processor.py             # process_photo 核心流程
├── api/v1/resume_builder.py           [MODIFY] 新增 3 个照片端点
├── domain/resume_builder/schemas.py   [MODIFY] ProcessedPhotoMeta；identity.photo 约定
├── infrastructure/rendering/
│   ├── html_renderer.py               [MODIFY] 注入 photo_data_uri
│   └── templates/*.html               [MODIFY] 三模板头像位（_macros.html 抽公共宏）
├── pyproject.toml                     [MODIFY] [project.optional-dependencies] imaging
frontend/src/pages/BuilderPage.tsx     [MODIFY] 照片卡片（上传/背景色/对照预览/确认）
frontend/src/api/builder.ts            [MODIFY] photo 三个 client 方法
backend/tests/
├── fixtures/photos/                   [NEW] face.jpg / no_face.jpg / two_faces.jpg
└── unit/test_photo_processor.py       [NEW]
```

## 核心算法（process_photo）

```
输入: data: bytes, bg_color: "white" | "blue" | "red"
1. Pillow 解码校验（失败 → ImageDecodeError）；EXIF 方向矫正；转 RGB
2. OpenCV Haar 检测人脸；0 张 → FaceNotFoundError；多张 → 取面积最大
3. 以人脸框为锚计算一寸裁剪框（295:413）：
   人脸水平居中；人脸高约占画面 40%；头顶留白 ≈ 画面高 7%；越界时向内收缩
4. rembg 抠图（u2net）→ RGBA；异常捕获 → 降级标记 degraded_reason，跳过 5
5. RGBA 合成到纯色背景（white=#FFFFFF / blue=#438EDB / red=#D43D3D）
6. ImageEnhance 温和增强：亮度 1.05 / 对比度 1.05 / 锐化 1.1
7. resize 到 295×413，输出 PNG bytes
返回: ProcessedPhoto(png_bytes, background_replaced: bool, degraded_reason: str | None)
```

## API 设计

沿用 `APIResponse{code, message, data}`；错误经 `HTTPException` 抛出。

| Method | Path | 说明 |
|---|---|---|
| POST | `/api/v1/resume-builder/{draft_id}/photo` | multipart `file`；query `bg_color=white`（默认）。校验 jpg/png、≤10MB → 处理 → 原图/结果写 MinIO → 返回预览 |
| PUT | `/api/v1/resume-builder/{draft_id}/photo/confirm` | body `{"object_name": "..."}`；校验对象属于该草稿 → 写入 `identity.photo` |
| DELETE | `/api/v1/resume-builder/{draft_id}/photo` | 清除 `identity.photo` 字段；MinIO 对象保留（可追溯） |

POST 成功响应 `data`：

```json
{
  "original_object": "photos/{draft_id}/original-{uuid8}.jpg",
  "processed_object": "photos/{draft_id}/processed-{uuid8}.png",
  "original_url": "<presigned>", "processed_url": "<presigned>",
  "background_replaced": true, "degraded_reason": null, "bg_color": "white"
}
```

## 错误分类

| 场景 | HTTP | message 码 |
|---|---|---|
| 非 jpg/png 或 >10MB | 400 | `INVALID_PHOTO` |
| 未检测到人脸 | 422 | `FACE_NOT_FOUND` |
| 图片损坏无法解码 | 400 | `PHOTO_DECODE_FAILED` |
| imaging 依赖未安装 | 501 | `IMAGING_NOT_AVAILABLE` |
| 抠图失败 | 200 | 降级成功，`degraded_reason` 说明 |
| confirm 对象名不属于该草稿 | 400 | `PHOTO_NOT_OWNED` |

## 模板渲染

- `_macros.html` 新增 `photo_block(photo_data_uri)` 宏；classic/modern/compact 姓名区右侧引用
- `identity.photo` 为空 → 宏输出空，flex 布局自然收合不留白
- `HtmlRenderer` 渲染前：草稿有 photo → 从 MinIO 读 bytes → `data:image/png;base64,...` 注入上下文
- 自动分页：照片高度固定（约 100px 内），多页布局和真实页数回归用例覆盖

## 测试策略

| US/FR | 测试 | 类型 |
|---|---|---|
| US-001 / FR-1~3 | `test_photo_processor.py`：人脸/无人脸/多人脸/降级 | unit |
| US-002 / FR-4,5,8 | API 上传/确认/删除/400/422/501 六路径（mock MinIO+processor） | unit |
| US-003 / FR-6,7 | 渲染快照 3 模板 × 有/无照片；分页测试带照片用例 | unit |
| US-004 | BuilderPage 四态 + 浏览器验证（dev-browser） | e2e |

## 实施顺序

1. `imaging/photo_processor.py` + 单测（US-001，无外部耦合可先行）
2. 照片 API 三端点 + MinIO 集成 + 单测（US-002，依赖 1）
3. 模板头像 + data URI 内联 + 渲染回归（US-003，依赖 2）
4. 前端照片卡片 + 浏览器验证（US-004，依赖 2/3）

## 风险与假设

- rembg 首次运行下载 u2net（约 170MB）：Docker 构建期预热（`python -c "from rembg import new_session; new_session()"`）[Assumption: 镜像体积可接受，否则照片美化拆独立 sidecar]
- Haar 对侧脸/遮挡检出率有限：允许用户直接使用原图（前端提供"跳过美化"），不阻塞导出
- presigned URL 有效期 1h，前端预览超时后重新请求详情接口刷新

---

## 验收标准

- [ ] 上传含人脸照片 → 返回一寸裁剪 + 背景替换（白/蓝/红）结果
- [ ] 无人脸照片 → HTTP 422 `FACE_NOT_FOUND`
- [ ] 抠图失败 → 降级"仅裁剪+增强"，响应携带 `degraded_reason`
- [ ] 原图与结果均落 MinIO，草稿仅在 confirm 后引用结果
- [ ] classic / modern / compact 三模板带照片与不带照片渲染均正常，自动分页不回归
- [ ] 单测：processor（人脸样张 fixture）、API 六路径、渲染快照
- [ ] 超过 10MB 或非 jpg/png → HTTP 400 `INVALID_PHOTO`
- [ ] imaging 依赖未安装 → HTTP 501 `IMAGING_NOT_AVAILABLE`
