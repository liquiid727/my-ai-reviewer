# RIP-003 — JD Matching

**Version**: v1.2 (as-built baseline correction)
**Status**: Implemented baseline (`rules_v1`); acceptance reconciliation pending issue #092
**Estimated**: Historical estimate 5-7 days
**Track**: Resume Intelligence Platform（PRD §8，原标"下一阶段"）
**Source**: `tasks/prd-parser.md` §8；增量：`tasks/prd-resume-toolchain-increments.md`（US-005~006 / FR-9~12）

---

## 目标

JD Matching 基线输入 ready JD（或兼容的 inline JD）与候选人 Profile，输出 **Skill Match / Missing Skills / Risk / Gap / Recommendation / Match Score**。当前交付是确定性的 `rules_v1`；Vision JD、多维 LLM 评分、硬条件筛选和版本化 freshness 由 RIP-010~RIP-012 定义。

## 现状

- `job_descriptions`、`jd_match_results`、匹配 API、JDExtractor 和 JD Library 前端代码均已存在。
- `rules_v1` 只读取 Candidate Profile 的 `skills`、`ability_tags`（以及未参与评分的 identity），不读取职责、工作经历、项目、教育或 Resume Facts。
- 关键技能和非关键技能分别按 70% / 30% 计算；缺少关键技能影响风险和 recommendation，但不是独立 hard filter。
- 当前匹配不调用 LLM、embedding 或向量库；代码存在与完整验收状态由 issue #092 分开核对。

## 技术栈

- LLM 文本 JD 抽取：required/preferred skills、responsibilities、seniority 及部分 evidence
- 确定性规则匹配：`profile.skills + ability_tags` vs `required_skills`
- 加权 Match Score：critical 70% / non-critical 30%
- 不包含向量检索或 LLM matching

## 数据模型（新增表）

### jd_match_results
| 字段 | 类型 | 说明 |
|---|---|---|
| id | UUID PK | |
| resume_id | FK → resumes | |
| jd_id | FK → job_descriptions（可空） | |
| skill_match | JSONB | 匹配明细 |
| missing_skills | JSONB | 缺失技能 |
| risk | JSONB | 风险点 |
| gap | text | 差距总结 |
| recommendation | text | 建议 |
| match_score | float | 0-100 |
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
  "jd_id": "uuid"
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

- [x] JD 结构化抽取（LLM：required/preferred skills / responsibilities / seniority）
- [x] 匹配算法：profile skills vs required → skill_match + missing_skills（`domain/jd/matching.py`，规则归一化）
- [x] 输出 risk / gap / recommendation / match_score
- [x] `POST /api/v1/jd/match` 接口
- [x] `jd_match_results` 落库
- [x] 前端 JD Library 与匹配触发入口（完整结果展示迁移到 RIP-012）
- [x] 单测（`tests/unit/test_jd_matching.py`）

---

# 增量设计（v1.1）：LLM JD 抽取器

> 来源：`tasks/prd-resume-toolchain-increments.md` US-005~006 / FR-9~12。该增量的实现已存在；本节保留历史设计，验收证据由 issue #092 核对。

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

- [x] `jd_extractor.py` 抽取 required_skills（含 critical + evidence）/ responsibilities / seniority
- [x] `POST /jd` 未显式传技能时自动抽取；显式传入时跳过（向后兼容）
- [x] 抽取失败 → 502 `JD_EXTRACTION_FAILED`，JD 不落库
- [x] 数据模型/迁移包含 responsibilities / seniority / extraction_source
- [x] 响应标记 `extraction_source: "llm" | "manual"`
- [ ] issue #092 复核上述路径的当前测试、lint 和 typecheck 证据
