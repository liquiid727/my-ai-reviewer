# Gear Tri-State Status Indicator

## Description

导航栏右上角齿轮增设明确的配置状态指示，呈现三态徽标，并在未就绪时醒目引导用户点击配置。

PRD Reference: US-A4 (tasks/prd-llm-gate-and-my-resumes.md)

## Acceptance Criteria

- [ ] 齿轮按钮（`frontend/src/components/Layout.tsx`）叠加状态徽标，呈现三态：
  - 未配置（无 active 配置）：红色/警示徽标 + 脉冲动画
  - 已配置未验证（有 active 但 `verified=false`）：黄色警示徽标
  - 已验证（active + verified）：绿色对勾徽标
- [ ] 未就绪时提供明显引导（齿轮旁文字/角标或 hover 提示"点击配置 AI 模型"）
- [ ] 徽标状态与就绪判定实时一致（配置变更/测试后更新）
- [ ] 视觉风格遵循 Neobrutalism（粗边框、鲜明配色、硬阴影）
- [ ] Typecheck 通过
- [ ] 在浏览器中验证三态显示

## Dependencies

Issue #15

## Type

frontend

## Priority

P1
