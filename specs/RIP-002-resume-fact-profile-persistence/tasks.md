# RIP-002 Tasks

**Feature**: Resume Fact & Profile Persistence
**Status**: Not Started
**Depends on**: RIP-001

---

## Task 列表

### T1 — ORM 模型
- [ ] `infrastructure/db/models.py`：新增 `ResumeFactModel`、`CandidateProfileModel`
- [ ] 字段对齐 `domain/resume/schemas.py`

### T2 — 数据库迁移
- [ ] Alembic 迁移建 `resume_facts`、`candidate_profiles`（FK + 索引）

### T3 — extract_facts 落库
- [ ] 改写 `domain/resume/services.py:extract_facts` 写入 `resume_facts`（每行一条 + evidence）

### T4 — classify_resume 落库
- [ ] 改写 `classify_resume` 写入 `candidate_profiles`
- [ ] 保留 `resumes` JSONB 兼容

### T5 — 查询接口
- [ ] `GET /api/v1/resume/{id}/facts`
- [ ] `GET /api/v1/resume/{id}/profile`

### T6 — 测试
- [ ] 单测：落库 + 查询
- [ ] 重解析：新 `parser_version` 追加而非覆盖（追溯）

---

## 依赖顺序

T1 → T2 → (T3, T4) → T5 → T6
