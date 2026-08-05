# Frontend Project Init + Upload Page

## Description

初始化 React + Vite + TypeScript 前端项目，集成 Tailwind CSS + Neobrutalism UI 组件库 + Zustand + React Router。实现全局 Layout 和简历上传页面。

PRD Reference: US-008
SPEC Reference: Section 2.5.1 ~ 2.5.8

## Acceptance Criteria

### 项目初始化
- [ ] `pnpm create vite frontend --template react-ts`
- [ ] 集成 Tailwind CSS（`@tailwindcss/vite` plugin）
- [ ] 初始化 Shadcn UI（`pnpm dlx shadcn@latest init`，CSS variables 模式）
- [ ] 安装 Neobrutalism UI 组件：Button, Card, Input, Label, Progress, Badge, Alert, Sonner, Skeleton
  - 安装方式：`pnpm dlx shadcn@latest add https://neobrutalism.dev/r/[component].json`
- [ ] 集成 Zustand（`pnpm add zustand`）
- [ ] 集成 React Router（`pnpm add react-router`）
- [ ] 配置路径别名 `@/` → `src/`
- [ ] Vite proxy 配置：`/api` → `http://localhost:8000`

### Layout 组件
- [ ] `src/components/Layout.tsx`：顶部导航栏 + 内容区域
- [ ] 导航栏：Logo/项目名（左）、"上传简历" 链接、"设置" 图标按钮（右，跳转 /settings）
- [ ] 使用 Neobrutalism Button 组件做导航

### Upload Page
- [ ] 页面路由：`/upload`，根路径 `/` 重定向到 `/upload`
- [ ] 拖拽上传区域 + 点击选择文件（自定义 `FileUploader` 组件）
- [ ] 文件格式提示：支持 PDF / DOCX / TXT / MD，最大 10MB
- [ ] 上传进度条（Neobrutalism Progress 组件）
- [ ] 格式错误 / 超限 → Sonner toast 错误提示
- [ ] 上传成功 → 显示"解析中"状态，自动轮询 `/api/v1/resume/{id}/status`（间隔 2s，3 分钟后降为 5s）
- [ ] 解析完成（status == "evaluated"）→ 自动跳转 `/resume/:id`
- [ ] 解析失败 → 显示错误信息 + 重试按钮
- [ ] 未配置 LLM 时 → Alert 提示"请先配置 AI 模型"+ 跳转 /settings 按钮
- [ ] `src/stores/resumeStore.ts`：管理 resumeId, status, isPolling 状态
- [ ] `src/api/client.ts` + `src/api/resume.ts`：API 调用封装
- [ ] `src/types/resume.ts`：TypeScript 类型定义
- [ ] 整体 UI 风格遵循 Neobrutalism 设计语言（粗边框、鲜明配色、硬阴影）
- [ ] Typecheck (tsc) 通过
- [ ] 在浏览器中验证完整上传流程

## Dependencies

Issue #3

## Type

frontend

## Priority

P1
