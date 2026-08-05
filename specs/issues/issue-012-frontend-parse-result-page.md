# Frontend Parse Result Page

## Description

实现简历解析结果展示页面，展示候选人 Profile、分区内容（教育/工作/项目/技能/证书），每项数据旁显示置信度和可展开的 Evidence 原文。

PRD Reference: US-009
SPEC Reference: Section 2.5.7 (Page 2: ResumeResultPage)

## Acceptance Criteria

- [ ] 页面路由：`/resume/:id`
- [ ] 调用 `GET /api/v1/resume/{id}` 获取解析数据
- [ ] 候选人信息卡片（ProfileCard 组件）：姓名、邮箱、电话、位置、链接
- [ ] 分类标签展示（Badge 组件，多色）：ability_tags
- [ ] 安装 Neobrutalism Tabs 组件：`pnpm dlx shadcn@latest add https://neobrutalism.dev/r/tabs.json`
- [ ] Tabs 切换展示：教育背景 / 工作经历 / 项目经历 / 技能 / 证书
- [ ] 每段经历用 Card 组件展示关键信息
- [ ] 置信度指示器（Badge variant）：绿色 confidence ≥ 0.8 / 黄色 ≥ 0.5 / 红色 < 0.5
- [ ] 安装 Neobrutalism Accordion 组件：`pnpm dlx shadcn@latest add https://neobrutalism.dev/r/accordion.json`
- [ ] Evidence 展开查看（Accordion 或 Tooltip）：显示 source_text + page 信息
- [ ] 数据未就绪时显示 Skeleton loading
- [ ] 底部"查看 AI 评估报告"按钮 → 跳转 `/resume/:id/evaluation`
- [ ] Typecheck 通过
- [ ] 在浏览器中验证页面展示效果

## Dependencies

Issue #10, Issue #5

## Type

frontend

## Priority

P1
