# Settings Page: Test-to-Verify

## Description

设置页对已保存配置点击"测试连接"成功后触发后端标记 `verified`，并在配置列表展示验证状态标签，明确引导用户测试通过后即可上传。

PRD Reference: US-A5 (tasks/prd-llm-gate-and-my-resumes.md)

## Acceptance Criteria

- [ ] `frontend/src/pages/SettingsPage.tsx` 对已保存配置点击"测试连接"成功后，触发后端标记该配置 `verified=true`
- [ ] 测试成功 Toast 明确指向下一步（如"已验证，可以开始上传简历"）
- [ ] 测试失败时该配置保持/回退为 `verified=false`，Toast 说明失败原因
- [ ] 配置列表 UI 展示每条配置的验证状态（已验证/未验证标签）
- [ ] 测试/保存后刷新就绪状态（联动齿轮与上传门禁）
- [ ] Typecheck 通过
- [ ] 在浏览器中验证：保存配置 → 测试通过 → 齿轮变绿 → 上传解锁

## Dependencies

Issue #14, Issue #15

## Type

frontend

## Priority

P2
