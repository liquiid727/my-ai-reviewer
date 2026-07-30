# RIP-002 — Resume Fact & Profile Persistence

**Version**: v1.0
**Status**: Done
**Estimated**: 4-5 天
**Track**: Resume Intelligence Platform（PRD §3）
**Source**: `tasks/prd-parser.md` §3；`tasks/spec-resume-input.md`（明确"第一版用 JSONB 存完整快照，后续按需拆表"）

---

## 目标

将 `ResumeFact` 与 `CandidateProfile`（当前仅为 `domain/resume/schemas.py` 中的 Pydantic 内存结构，未落库）持久化为独立数据库表，真正实现 PRD 强调的"**可追溯 Fact 抽取**"与"**Candidate Profile 标准化**"。当前 facts/profile 以 JSON 存入 `resumes` 表，无法按 Fact / Section 检索或审计。

## 现状

- `domain/resume/schemas.py`：`ResumeFact`、`CandidateProfile`、`Evidence`、`Skill`（Pydantic 模型，仅内存）
- `domain/resume/entities.py`：空（DDD 实体未建模）
- `infrastructure/db/models.py`：仅 `ResumeModel`（含 JSON 结果），无 `ResumeFactModel` / `CandidateProfileModel`
- `domain/resume/services.py`：`extract_facts()`、`classify_resume()` 把结果写回 `resumes` JSON

## 技术栈

- SQLAlchemy 2 ORM 模型 + Alembic 迁移（async）
- PostgreSQL JSONB 用于半结构化 `value` / `skills` 字段

## 数据模型（新增表）

### resume_facts
| 字段 | 类型 | 说明 |
|---|---|---|
| id | UUID PK | |
| resume_id | FK → resumes | |
| fact_type | str | skill / education / work / project / certificate |
| fact_key | str | 归一化键（如 "Redis"） |
| value | JSONB | 结构化值 |
| evidence_source_text | str | 原文片段 |
| evidence_section | str | 来源 Section |
| evidence_confidence | float | 置信度 |
| page | int | 来源页码（可空） |
| parser_version | str | 解析器版本（追溯） |
| created_at | ts | |

### candidate_profiles
| 字段 | 类型 | 说明 |
|---|---|---|
| id | UUID PK | |
| resume_id | FK → resumes (unique) | |
| identity | JSONB | 身份 |
| education | JSONB | 教育 |
| work | JSONB | 工作 |
| projects | JSONB | 项目 |
| skills | JSONB | 技能 |
| ability_tags | JSONB | 能力标签（backend / ai_engineer ...） |
| years | int | 工作年限 |
| industry | str | 行业 |
| architecture_exp | bool | 架构经验 |
| ai_exp | bool | AI 经验 |
| cloud_exp | bool | 云经验 |
| leadership | bool | 管理经验 |
| created_at | ts | |

## 接口/行为

- `extract_facts()` 改写：每条 Fact 写入 `resume_facts`（含 Evidence / Confidence / Section / Page / parser_version）
- `classify_resume()` 改写：写入 `candidate_profiles` 一行
- 查询：`GET /api/v1/resume/{id}/facts`、`GET /api/v1/resume/{id}/profile`
- 保留 `resumes` 表 JSON 兼容（历史数据仍可读）

## 验收标准

- [ ] 定义 `ResumeFactModel` 与 `CandidateProfileModel`
- [ ] Alembic 迁移建表（含 FK 与索引）
- [ ] `extract_facts` 落库每行 fact（保留 evidence 字段）
- [ ] `classify_resume` 落库 profile
- [ ] 新增查询接口：`/resume/{id}/facts`、`/resume/{id}/profile`
- [ ] 保留 `resumes` JSONB 兼容（历史数据可读）
- [ ] 单测：落库与查询
