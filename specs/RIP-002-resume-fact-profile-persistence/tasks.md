# RIP-002 Tasks

**Feature**: Resume Fact & Profile Persistence
**Status**: Done
**Depends on**: RIP-001

---

## Task 列表

### T1 — ORM 模型
- [x] `infrastructure/db/models.py`：新增 `ResumeFactModel`、`CandidateProfileModel`（另含 `ResumeSectionModel`）
- [x] 字段对齐 `domain/resume/schemas.py`

### T2 — 数据库迁移
- [x] Alembic 迁移建 `resume_facts`、`candidate_profiles`（FK + 索引；`b2c3d4e5f6a7_add_resume_intelligence_tables`）

### T3 — extract_facts 落库
- [x] `domain/resume/services.py:extract_facts` 经 `_persist_facts` 写入 `resume_facts`（每行一条 + evidence）

### T4 — classify_resume 落库
- [x] `classify_resume` 经 `_upsert_candidate_profile` 写入 `candidate_profiles`
- [x] 保留 `resumes` JSONB 兼容（`parsed_result` 字段）

### T5 — 查询接口
- [x] `GET /api/v1/resume/{id}/facts`
- [x] `GET /api/v1/resume/{id}/profile`

### T6 — 测试
- [x] 单测：落库 + 查询（`tests/unit` + `tests/integration`）
- [x] 重解析：`snapshot_and_reset_for_reparse` 新 `parser_version` 追加而非覆盖（`test_reparse.py`）

---

## 依赖顺序

T1 → T2 → (T3, T4) → T5 → T6
