# RIP-003 — JD Matching

**Version**: v1.0
**Status**: Not Started（规划中）
**Estimated**: 5-7 天
**Track**: Resume Intelligence Platform（PRD §8，原标"下一阶段"）
**Source**: `docs/prd/parser.md` §8

---

## 目标

新增 JD Matching 模块：输入 JD 文本 + 候选人 Profile，输出 **Skill Match / Missing Skills / Risk / Gap / Recommendation / Match Score**。PRD §8 标为"下一阶段"，当前无任何实现（`job_descriptions` 表已在 `design/database.md` 规划，但无匹配逻辑与结果表）。

## 现状

- `design/database.md` 已有 `job_descriptions` 表，但无字段定义、无匹配结果表
- Interview 流程已接受 `jd_text` 输入，但未做结构化匹配
- `CandidateProfile`（RIP-002 落库后）提供技能 / 经验基线

## 技术栈

- LLM 从 JD 抽取 required_skills / responsibilities / seniority
- 规则 + 向量混合匹配：profile.skills vs required_skills
- 加权 Match Score

## 数据模型（新增表）

### jd_match_results
| 字段 | 类型 | 说明 |
|---|---|---|
| id | UUID PK | |
| resume_id | FK → resumes | |
| jd_id | FK → job_descriptions（可空） | |
| required_skills | JSONB | JD 抽取结果 |
| skill_match | JSONB | 匹配明细 |
| missing_skills | JSONB | 缺失技能 |
| risk | JSONB | 风险点 |
| gap | text | 差距总结 |
| recommendation | text | 建议 |
| match_score | float | 0-100 |
| llm_model | str | |
| created_at | ts | |

`job_descriptions` 补充字段：`required_skills`(JSONB)、`responsibilities`(JSONB)、`seniority`(str)

## 接口定义

### JD 匹配
```http
POST /api/v1/jd/match
Content-Type: application/json

Body:
{
  "resume_id": "uuid",
  "jd_text": "招聘高级后端工程师，要求 Go + Kubernetes + 高并发经验"
}

Response:
{
  "skill_match": [{ "skill": "Go", "matched": true, "level": "proficient" }],
  "missing_skills": ["Kubernetes"],
  "risk": ["缺少高并发项目经验"],
  "gap": "云原生深度不足",
  "recommendation": "建议作为二面候选人，重点追问分布式经验",
  "match_score": 82
}
```

## 验收标准

- [ ] JD 结构化抽取（LLM：required_skills / responsibilities / seniority）
- [ ] 匹配算法：profile skills vs required → skill_match + missing_skills
- [ ] 输出 risk / gap / recommendation / match_score
- [ ] `POST /api/v1/jd/match` 接口
- [ ] `jd_match_results` 落库
- [ ] 前端 JD 输入 + 匹配结果页（可选）
- [ ] 单测
