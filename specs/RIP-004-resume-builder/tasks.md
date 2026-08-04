# RIP-004 Tasks

**Feature**: Resume Builder（制作 / 润色 / 照片美化）
**Status**: Partially Implemented（T1-T4 已完成，T5-T7 照片美化待做）
**Depends on**: RIP-002

---

## Task 列表

### T1 — 草稿域模型与服务（已完成）
- [x] `domain/resume_builder/schemas.py`：Draft / Section / Item / DesignTokens
- [x] `domain/resume_builder/services.py`：`profile_to_draft`、草稿 CRUD
- [x] DB：`ResumeDraftModel` / `ResumeExportModel` + 迁移 `d4e5f6a7b8c9`

### T2 — 模板渲染与导出（已完成）
- [x] Jinja2 三模板：classic / modern / compact
- [x] `PdfRenderer`：Playwright 打印 A4（分页策略由 RIP-005 接管）
- [x] `/preview`、`/export`（可持久化 MinIO）

### T3 — AI 润色与评分（已完成）
- [x] `LLMResumePolisher`：保留原文、逐条建议
- [x] `polish_draft_section` / `score_draft` + `/polish`、`/score` API

### T4 — 前端 Builder 页（已完成）
- [x] `frontend/src/pages/BuilderPage.tsx`：编辑 / 润色 / 预览 / 导出

### T5 — 照片处理器
- [ ] 引入 `opencv-python-headless`、`rembg`（写入 `backend/pyproject.toml`）
- [ ] `infrastructure/imaging/photo_processor.py`：人脸检测 → 一寸裁剪 → 抠图换底（白/蓝/红）→ 增强
- [ ] 错误与降级：`FaceNotFoundError`；抠图失败降级为"仅裁剪+增强"

### T6 — 照片 API 与草稿集成
- [ ] `POST /resume-builder/{draft_id}/photo`（上传+处理，≤10MB，jpg/png）
- [ ] `PUT /{draft_id}/photo/confirm` / `DELETE /{draft_id}/photo`
- [ ] `identity.photo` 写入草稿；原图与结果落 MinIO

### T7 — 模板头像与测试
- [ ] 三模板头像占位（无照片不留白）；导出 PDF 照片 data URI 内联
- [ ] 单测：processor（人脸样张 fixture）、API、渲染快照、自动分页回归
- [ ] 前端 BuilderPage：照片上传 / 背景色选择 / 预览确认（Empty/Loading/Success/Failure 四态）

---

## 依赖顺序

T1 → T2 → (T3, T4)（已完成）→ T5 → T6 → T7
