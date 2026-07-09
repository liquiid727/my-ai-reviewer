# Frontend Evaluation Report Page

## Description

实现 AI 评估报告页面，展示综合评分（环形进度）、多维度雷达图、优势/风险分析、面试建议和综合评价。

PRD Reference: US-010
SPEC Reference: Section 2.5.7 (Page 3: EvaluationPage)

## Acceptance Criteria

- [ ] 页面路由：`/resume/:id/evaluation`
- [ ] 调用 `GET /api/v1/resume/{id}/evaluation` 获取评估数据
- [ ] 综合评分醒目展示：自定义 ScoreGauge 组件（SVG 环形进度 + 大数字）
- [ ] 安装 Recharts：`pnpm add recharts`
- [ ] 维度评分：Recharts RadarChart 雷达图展示 8 个维度
- [ ] 每个维度可 hover 或点击查看 reason + evidence 详情
- [ ] 优势列表（Card 组件 + 绿色 Badge）：3-5 条，每条显示 point + evidence
- [ ] 风险列表（Card 组件 + 红色/黄色 Badge）：每条显示 point + evidence + severity 标签
- [ ] 安装 Neobrutalism Accordion：`pnpm dlx shadcn@latest add https://neobrutalism.dev/r/accordion.json`（如未安装）
- [ ] 面试建议区域（Accordion 4 组）：值得追问(N) / 疑似夸大(N) / 验证方向(N) / 建议跳过(N)
- [ ] Summary 综合评价（Alert info variant 突出展示）
- [ ] 评估仍在进行时 → Skeleton + indeterminate Progress 动画
- [ ] 评估失败 → 显示错误信息 + 重试按钮
- [ ] Typecheck 通过
- [ ] 在浏览器中验证报告展示效果

## Dependencies

Issue #10, Issue #7

## Type

frontend

## Priority

P1
