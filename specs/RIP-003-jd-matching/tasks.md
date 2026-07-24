# RIP-003 Tasks

**Feature**: JD Matching
**Status**: Not Started（规划中）
**Depends on**: RIP-002

---

## Task 列表

### T1 — JD 抽取器
- [ ] `infrastructure/extractors/jd_extractor.py`：LLM 从 JD 抽取 required_skills / responsibilities / seniority
- [ ] 结果写入 `job_descriptions`（补充字段）

### T2 — 匹配算法
- [ ] `infrastructure/matchers/jd_matcher.py`：profile.skills vs required → skill_match / missing_skills
- [ ] 计算 risk / gap / recommendation / match_score

### T3 — API 接口
- [ ] `api/v1/jd.py`：`POST /jd/match`
- [ ] 结果落库 `jd_match_results`

### T4 — 数据模型与迁移
- [ ] `infrastructure/db/models.py`：新增 `JDModel`（补充字段）、`JDMatchResultModel`
- [ ] Alembic 迁移建表

### T5 — 测试
- [ ] 单测：抽取 + 匹配 + API

### T6 — 前端（可选）
- [ ] JD 输入 + 匹配结果展示页

---

## 依赖顺序

T1 → T2 → T3 → (T4, T5) → T6（可选）
