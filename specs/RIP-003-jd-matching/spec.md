# RIP-003 — JD Matching

**Version**: v1.1
**Status**: Mostly Done（残留见 tasks.md：LLM JD 抽取器、前端页）
**Estimated**: 5-7 天（已完成主体；残留 LLM 抽取器约 1-2 天）
**Track**: Resume Intelligence Platform（PRD §8，原标"下一阶段"）
**Source**: `tasks/prd-parser.md` §8；增量：`tasks/prd-resume-toolchain-increments.md`（US-005~006 / FR-9~12）

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

- [ ] JD 结构化抽取（LLM：required_skills / responsibilities / seniority）——见下方增量设计
- [x] 匹配算法：profile skills vs required → skill_match + missing_skills（`domain/jd/matching.py`，规则归一化）
- [x] 输出 risk / gap / recommendation / match_score
- [x] `POST /api/v1/jd/match` 接口
- [x] `jd_match_results` 落库
- [ ] 前端 JD 输入 + 匹配结果页（可选，另行排期）
- [x] 单测（`tests/unit/test_jd_matching.py`）

---

# 增量设计（v1.1）：LLM JD 抽取器

> 来源：`tasks/prd-resume-toolchain-increments.md` US-005~006 / FR-9~12。现状：`POST /jd` 要求调用方手工传入 `required_skills`，真实用户只会粘贴 JD 原文。

## 设计决策

| 决策 | 选择 | 理由 |
|---|---|---|
| 抽取器位置 | `infrastructure/extractors/jd_extractor.py` | 与 `llm_extractor.py`（简历抽取）同目录同模式，复用 `LLMGateway` |
| 触发时机 | `POST /jd` 未传 `required_skills` 且 `raw_text` 非空时 | FR-12 向后兼容：显式传入则跳过抽取 |
| 失败语义 | HTTP 502 `JD_EXTRACTION_FAILED`，JD 不落库 | FR-11 不产生半成品；与简历抽取失败语义一致 |
| evidence | 每项技能附原文片段 | FR-10，与 Fact 体系口径一致，可解释 |
| seniority 枚举 | junior / mid / senior / expert | PRD 假设，后续与面试难度体系对齐 |

## 组件与文件

```
backend/
├── infrastructure/extractors/jd_extractor.py   [NEW]  JDExtractor.extract(raw_text) -> JDExtraction
├── domain/jd/schemas.py                        [MODIFY] JDExtraction / ExtractedSkill(evidence) 模型
├── api/v1/jd.py                                [MODIFY] POST /jd 接入自动抽取分支
├── infrastructure/db/models.py                 [MODIFY] JobDescriptionModel + responsibilities/seniority/extraction_source
├── infra/alembic/versions/xxxx_add_jd_extraction_fields.py  [NEW]
└── tests/unit/test_jd_extractor.py             [NEW]  mock LLMGateway
```

## 抽取输出结构（Pydantic）

```json
{
  "required_skills": [
    {"name": "Go", "critical": true, "evidence": "精通 Go 语言，3 年以上经验"}
  ],
  "responsibilities": ["负责核心服务架构设计"],
  "seniority": "senior"
}
```

## 行为变更（POST /jd）

- 传了 `required_skills` → 行为不变，`extraction_source="manual"`
- 未传且 `raw_text` 非空 → 调用 `JDExtractor` → 成功落库（含 responsibilities / seniority），`extraction_source="llm"`；失败 → 502，不落库
- 响应 data 新增 `extraction_source` 字段
- LLM 输出不合法（非 JSON / 缺字段）→ 抽取器内部重试 1 次后抱错，不返回半成品

## 测试策略

| US/FR | 测试 | 类型 |
|---|---|---|
| US-005 / FR-9,10 | `test_jd_extractor.py`：正常抽取 / 输出格式异常（mock 网关） | unit |
| US-006 / FR-11,12 | `test_jd_matching.py` 扩展：自动抽取 / 手动传入 / 抽取失败三路径 | unit |

## 增量验收标准

- [ ] `jd_extractor.py` 抽取 required_skills（含 critical + evidence）/ responsibilities / seniority
- [ ] `POST /jd` 未传技能时自动抽取；显式传入时跳过（向后兼容）
- [ ] 抽取失败 → 502 `JD_EXTRACTION_FAILED`，JD 不落库
- [ ] 新增 Alembic 迁移：responsibilities / seniority / extraction_source
- [ ] 响应标记 `extraction_source: "llm" | "manual"`
- [ ] 单测覆盖上述全部路径；lint / mypy 通过
