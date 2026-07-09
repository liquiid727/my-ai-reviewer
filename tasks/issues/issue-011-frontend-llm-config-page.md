# Frontend LLM Config Page

## Description

实现 LLM 模型配置页面，用户可选择 Provider、填写 API Key、选择模型、测试连接并保存配置。

PRD Reference: US-012
SPEC Reference: Section 2.5.7 (Page 4: SettingsPage)

## Acceptance Criteria

- [ ] 页面路由：`/settings`
- [ ] 导航栏"设置"按钮跳转至此页面
- [ ] Provider 下拉选择（Neobrutalism Select 组件）：OpenAI / Claude (Anthropic) / DeepSeek / Custom
- [ ] 根据 Provider 动态显示模型列表（Select 组件）：
  - OpenAI: gpt-4o, gpt-4o-mini, gpt-4-turbo, o3-mini
  - Claude: claude-sonnet-4-20250514, claude-haiku-4-5-20251001, claude-opus-4-20250514
  - DeepSeek: deepseek-chat, deepseek-reasoner
  - Custom: 显示 Input 手动填写 model name
- [ ] API Key 输入框（Input type=password）+ 显示/隐藏切换按钮
- [ ] Base URL 输入框（仅 Custom provider 时必填，其他 provider 可选）
- [ ] "测试连接" 按钮（Button secondary variant）：调用 `POST /api/v1/settings/llm/test`
- [ ] 测试成功 → 显示绿色提示 + 可用模型列表
- [ ] 测试失败 → 显示红色错误信息
- [ ] "保存配置" 按钮（Button default variant）：调用 `POST /api/v1/settings/llm`
- [ ] 保存成功 → Sonner toast 成功提示
- [ ] 已保存配置列表（Table 或 Card 列表）：显示 provider, model, masked key, 编辑/删除操作
- [ ] `src/stores/settingsStore.ts`：管理 LLM 配置状态
- [ ] `src/api/settings.ts`：API 调用封装
- [ ] `src/types/settings.ts`：TypeScript 类型定义
- [ ] Typecheck 通过
- [ ] 在浏览器中验证配置流程：选择 Provider → 填写 Key → 测试连接 → 保存

## Dependencies

Issue #10, Issue #9

## Type

frontend

## Priority

P1
