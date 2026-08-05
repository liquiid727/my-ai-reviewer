# LLM Config Verified State (Backend)

## Description

为 LLM 配置增加"已验证"状态，作为简历上传硬门禁的判定依据。连接测试通过后将对应已保存配置标记为已验证；配置关键字段变更时重置为未验证。`verified` 不设时间过期。

PRD Reference: US-A1 (tasks/prd-llm-gate-and-my-resumes.md)

## Acceptance Criteria

- [x] `llm_configs` 表新增字段：`verified`(bool, 默认 false)、`last_verified_at`(datetime, 可空)
- [x] Alembic 迁移脚本创建，向后兼容（已有配置默认 `verified=false`）
- [x] `POST /api/v1/settings/llm/test` 支持可选 `config_id`：命中已保存配置时，测试通过则置 `verified=true` 并更新 `last_verified_at`，测试失败置 `verified=false`；不传 `config_id` 时保持"仅测试不落库"行为
- [x] `PUT /api/v1/settings/llm/{id}` 更新 `api_key`/`provider`/`model_name`/`base_url` 任一字段时，`verified` 重置为 `false`
- [x] `verified` 一旦置 true 不设过期，仅在配置关键字段变更或测试失败时失效
- [x] `_serialize`（`backend/api/v1/settings.py`）在响应中返回 `verified` 与 `last_verified_at`
- [x] `backend/application/llm_config_service.py` 补充相应业务逻辑
- [x] Typecheck 通过

## Dependencies

None

## Type

backend

## Priority

P1
