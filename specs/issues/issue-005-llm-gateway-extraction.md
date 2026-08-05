# LLM Gateway + Structured Extraction

## Description

实现 LLM Gateway 抽象层（支持 OpenAI/Anthropic/DeepSeek/Custom），以及基于 LLM 的简历结构化信息抽取。使用 JSON Mode/Structured Output 确保输出格式可控。所有抽取结果附带 Evidence 追溯。

PRD Reference: US-004
SPEC Reference: Section 5.3, 5.6, 5.8

## Acceptance Criteria

- [ ] `backend/infrastructure/llm/providers/base.py`：LLMProvider ABC + LLMResponse 数据类
- [ ] `backend/infrastructure/llm/providers/openai_provider.py`：使用 openai SDK（AsyncOpenAI），支持自定义 base_url（兼容 DeepSeek/Custom）
- [ ] `backend/infrastructure/llm/providers/anthropic_provider.py`：使用 anthropic SDK（AsyncAnthropic），处理 OpenAI→Anthropic 消息格式转换
- [ ] `backend/infrastructure/llm/gateway.py`：LLMGateway 根据 provider 类型路由到对应实现
- [ ] LLMResponse 包含：content, model, usage（prompt_tokens, completion_tokens）
- [ ] `backend/infrastructure/llm/prompts/extraction.py`：抽取 system prompt
- [ ] `backend/infrastructure/extractors/base.py`：ResumeExtractor ABC
- [ ] `backend/infrastructure/extractors/llm_extractor.py`：调用 LLMGateway 进行结构化抽取
- [ ] LLM 输出包含：sections（按 ResumeSectionType 分类）、facts（ResumeFact 列表，含 evidence）、profile（CandidateProfile）
- [ ] 使用 JSON Mode / response_format={"type": "json_object"} 强制格式
- [ ] 输出解析后验证符合 Pydantic schema，验证失败重试 1 次
- [ ] 抽取结果保存到 `resumes.parsed_result`（JSONB）
- [ ] 记录 token_usage 和 model 信息
- [ ] 状态更新为 `fact_extracted`
- [ ] 超长文本（>30000 字）截断处理
- [ ] 优先使用用户 LLM 配置（llm_configs 表），未配置则用系统默认（环境变量）
- [ ] Typecheck 通过

## Dependencies

Issue #4

## Type

backend

## Priority

P0
