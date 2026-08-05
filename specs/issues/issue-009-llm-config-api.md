# LLM Config CRUD API + Encryption

## Description

实现 LLM 配置管理的 CRUD API，支持 OpenAI/Anthropic/DeepSeek/Custom 四种 Provider。API Key 使用 Fernet 加密存储，提供连接测试端点。

PRD Reference: US-011
SPEC Reference: Section 4.1, 4.2, 7.1

## Acceptance Criteria

- [ ] `backend/infrastructure/crypto/encryption.py`：APIKeyEncryptor（Fernet 加密/解密/脱敏）
- [ ] 加密密钥通过环境变量 `ENCRYPTION_KEY` 注入
- [ ] `POST /api/v1/settings/llm`：保存 LLM 配置（provider, api_key, model_name, base_url）
- [ ] `GET /api/v1/settings/llm`：获取所有配置列表，api_key 脱敏返回（如 "sk-...4f2c"）
- [ ] `PUT /api/v1/settings/llm/{id}`：更新已有配置
- [ ] `DELETE /api/v1/settings/llm/{id}`：删除配置
- [ ] `POST /api/v1/settings/llm/test`：测试连接（调用 provider 的 models API 验证 Key 有效性）
- [ ] 支持 Provider 枚举：openai, anthropic, deepseek, custom
- [ ] 连接测试超时 15s
- [ ] 测试成功返回可用模型列表，失败返回错误信息
- [ ] `backend/api/v1/settings.py` 路由
- [ ] `backend/application/llm_config_service.py` 业务逻辑
- [ ] Typecheck 通过

## Dependencies

Issue #2

## Type

backend

## Priority

P1
