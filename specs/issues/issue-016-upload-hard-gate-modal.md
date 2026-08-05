# Upload Hard Gate + Guidance Modal

## Description

在 LLM 未就绪（不存在 active+verified 配置）时硬拦截简历上传：禁用上传区，点击时弹窗说明并引导用户去设置页配置与测试。覆盖无配置、有配置未测试、测试失败三种阻断态。

PRD Reference: US-A3 (tasks/prd-llm-gate-and-my-resumes.md)

## Acceptance Criteria

- [ ] 进入上传页（`frontend/src/pages/UploadPage.tsx`）时若 LLM 未就绪，上传区域禁用（拖拽/点击选择均不触发上传）
- [ ] 用户点击上传/选择文件时，立即弹出提示 Modal，说明"需先配置并测试 AI 模型后才能上传简历"
- [ ] Modal 提供主操作按钮"去配置"跳转 `/settings`，次要"取消"关闭
- [ ] 拦截覆盖三种未就绪态：无配置、有配置但 `verified=false`、测试失败
- [ ] 就绪后上传区域恢复可用，正常走原有上传流程
- [ ] 原有软文字提示（`upload.tip`）与门禁状态保持一致
- [ ] 视觉风格遵循 Neobrutalism
- [ ] Typecheck 通过
- [ ] 在浏览器中验证：无配置被拦截 → 去配置测试通过 → 回到上传页可正常上传

## Dependencies

Issue #15

## Type

frontend

## Priority

P1
