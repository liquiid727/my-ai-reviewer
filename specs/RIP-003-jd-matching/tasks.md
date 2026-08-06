# RIP-003 Tasks

**Feature**: JD Matching
**Status**: Implemented baseline (`rules_v1`); acceptance reconciliation pending issue #092
**Depends on**: RIP-002

---

## Task 列表

### T1 — JD 抽取器
- [x] LLM 从 raw_text 抽取 required/preferred skills / responsibilities / seniority；legacy `POST /jd` 在未显式传技能时自动调用
- [x] 结果写入 `job_descriptions`（required_skills JSONB）

### T2 — 匹配算法
- [x] 实现于 `domain/jd/policies.py`（确定性 `rules_v1`，非 LLM/向量）：profile.skills + ability_tags vs required → skill_match / missing_skills
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
- [x] JD Library 页面/API client 和匹配触发入口已存在
- [ ] 多维匹配结果展示、stale/recompute 由 RIP-012 issue #103 交付

### T7 — 漂移复核
- [ ] issue #092 将代码存在状态映射到迁移、单元、集成和浏览器验收证据

---

## 依赖顺序

T1 → T2 → T3 → (T4, T5) → T6（可选）
