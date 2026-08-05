# Database Schema + Alembic Migrations

## Description

配置 SQLAlchemy 2.x async ORM 和 Alembic 迁移工具，创建所有数据表（users, files, resumes, resume_evaluations, llm_configs）。定义 ORM 模型和关联关系。

PRD Reference: US-001
SPEC Reference: Section 3.1, 3.2, 3.3, 3.4

## Acceptance Criteria

- [ ] `backend/infrastructure/db/database.py` 配置 async SQLAlchemy engine + session
- [ ] `backend/infrastructure/db/models.py` 定义所有 ORM 模型：UserModel, FileModel, ResumeModel, ResumeEvaluationModel, LLMConfigModel
- [ ] Alembic 初始化配置（`alembic.ini` + `alembic/env.py`）
- [ ] 创建初始迁移：`alembic revision --autogenerate -m "create_initial_tables"`
- [ ] `alembic upgrade head` 成功执行，所有表创建完成
- [ ] `resumes` 表：独立实体（无 interview_id 外键），包含 status, raw_text, parsed_result(JSONB), parser_version, parse_error
- [ ] `resume_evaluations` 表：overall_score, dimension_scores(JSONB), strengths(JSONB), risks(JSONB), interview_suggestions(JSONB), summary, llm_model
- [ ] `llm_configs` 表：provider, api_key_encrypted, model_name, base_url, is_active
- [ ] `files` 表：sha256_hash 有索引，支持 owner_type + owner_id 多态关联
- [ ] `backend/domain/resume/enums.py` 增加 `EVALUATED = "evaluated"` 状态和 `LLMProvider` 枚举
- [ ] `backend/domain/resume/schemas.py` 增加 `DimensionScore`, `ResumeEvaluation` Pydantic 模型
- [ ] `backend/infrastructure/db/repositories.py` 提供基础 CRUD 方法（create, get_by_id, update）
- [ ] Typecheck 通过

## Dependencies

Issue #1

## Type

backend

## Priority

P0
