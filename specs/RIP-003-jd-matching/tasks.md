# RIP-003 Tasks

**Feature**: JD Matching
**Status**: Mostly Done（残留：LLM JD 抽取器、前端页）
**Depends on**: RIP-002

---

## Task 列表

### T1 — JD 抽取器
- [ ] LLM 从 raw_text 抽取 required_skills / responsibilities / seniority（未做：当前 `POST /jd` 由调用方直接传入 required_skills / critical_skills）
- [x] 结果写入 `job_descriptions`（required_skills JSONB）

### T2 — 匹配算法
- [x] 实现于 `domain/jd/matching.py`（偏差：非 `infrastructure/matchers/`；规则归一化匹配，非 LLM）：profile.skills vs required → skill_match / missing_skills
- [x] 计算 risk / gap / recommendation / match_score（`_compute_match` + `JDMatchingService`）

### T3 — API 接口
- [x] `api/v1/jd.py`：`POST /jd`、`GET /jd/{id}`、`POST /jd/match`
- [x] 结果落库 `jd_match_results`

### T4 — 数据模型与迁移
- [x] `infrastructure/db/models.py`：`JobDescriptionModel`、`JDMatchResultModel`
- [x] Alembic 迁移建表（`b2c3d4e5f6a7_add_resume_intelligence_tables`）

### T5 — 测试
- [x] 单测：匹配 + API（`tests/unit/test_jd_matching.py`）

### T6 — 前端（可选）
- [ ] JD 输入 + 匹配结果展示页（未做：前端无 JD 页面 / api client）

---

## 依赖顺序

T1 → T2 → T3 → (T4, T5) → T6（可选）
