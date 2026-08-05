# SPEC: Resume Input Pipeline

> Technical specification derived from: `tasks/prd-resume-input.md`
> Generated: 2026-07-08

## 1. Summary

### 1.1 What This SPEC Covers

本文档为简历输入管道的技术实现规格。覆盖从简历文件上传（PDF/DOCX/TXT/MD）到 AI 多维度评估的完整后端 Pipeline，以及前端三个核心页面（上传、解析结果、评估报告）和 LLM 配置管理功能。

### 1.2 PRD Reference
- Source: `tasks/prd-resume-input.md`
- User Stories covered: US-001 ~ US-012
- Functional Requirements covered: FR-1 ~ FR-12

### 1.3 Design Decisions Summary

| Decision | Choice | Rationale |
|----------|--------|-----------|
| PDF 解析库 | PyMuPDF (`pymupdf`) | 比 pypdf 更稳定，支持复杂布局和表格提取 |
| DOCX 解析库 | python-docx | 轻量，覆盖 DOCX 段落+表格提取 |
| LLM 调用方式 | OpenAI 兼容格式（openai SDK） | 统一接口，支持多 provider 切换 |
| Anthropic 接入 | anthropic SDK + OpenAI 兼容适配层 | Claude 不完全兼容 OpenAI 格式，需适配 |
| Fact 存储 | `resumes.parsed_result` JSONB 字段 | 第一版用 JSONB 存完整快照，后续按需拆表 |
| 评估结果存储 | 独立 `resume_evaluations` 表 | 与面试评分(`evaluations`)区分，支持独立查询 |
| Resume 关联 | 独立实体，不绑定 interview_id | 简历先上传评估，后续面试时关联 |
| 异步框架 | Celery + Redis broker | 符合现有架构设计，成熟稳定 |
| 前端框架 | React + Vite + TypeScript | 轻量，开发体验好，HMR 快 |
| 状态管理 | Zustand | API 简洁，TypeScript 友好，无 boilerplate |
| UI 组件库 | Neobrutalism UI (基于 Shadcn UI) | 50+ 组件，粗边框+硬阴影 Neobrutalism 风格，通过 `pnpm dlx shadcn@latest add https://neobrutalism.dev/r/[component].json` 安装 |
| 图表库 | Recharts | 雷达图、条形图，React 生态，轻量 |
| API Key 加密 | Fernet (cryptography) | Python 生态标准对称加密，简单可靠 |
| Parser 模式 | ABC 基类 + 版本号 | 复用 `parse.md` 已有模式，支持升级 |

---

## 2. Architecture

### 2.1 System Context

```
┌─────────────────────────────────────────────────────────┐
│                    Frontend (React + Vite)               │
│  /upload  →  /resume/:id  →  /resume/:id/evaluation     │
│  /settings (LLM Config)                                  │
└──────────────────────┬──────────────────────────────────┘
                       │ HTTP (REST API)
┌──────────────────────▼──────────────────────────────────┐
│                 FastAPI (API Gateway)                     │
│  /api/v1/resume/*   /api/v1/settings/*   /api/health     │
└──────┬───────────────────────────────┬──────────────────┘
       │                               │
       ▼                               ▼
┌──────────────┐              ┌────────────────┐
│ Application  │              │  Celery Worker  │
│   Services   │──trigger──▶  │  (Async Tasks)  │
└──────┬───────┘              └───────┬────────┘
       │                              │
       ▼                              ▼
┌──────────────────────────────────────────────────────────┐
│                    Domain Layer                           │
│  Resume Domain: Entities, Value Objects, Domain Services  │
└──────────────────────────┬───────────────────────────────┘
                           │
┌──────────────────────────▼───────────────────────────────┐
│                  Infrastructure Layer                      │
│  ┌─────────┐  ┌────────┐  ┌───────┐  ┌────────────────┐ │
│  │ Parsers │  │  LLM   │  │ MinIO │  │  PostgreSQL    │ │
│  │PDF/DOCX │  │Gateway │  │Storage│  │  (SQLAlchemy)  │ │
│  └─────────┘  └────────┘  └───────┘  └────────────────┘ │
│  ┌──────────────┐  ┌───────────────┐                     │
│  │  Extractors  │  │  Classifiers  │                     │
│  │  (LLM-based) │  │ (Rule-based)  │                     │
│  └──────────────┘  └───────────────┘                     │
└──────────────────────────────────────────────────────────┘
```

### 2.2 Component Design

| Component | Responsibility | Layer |
|-----------|---------------|-------|
| `ResumeRouter` | HTTP 路由，请求验证，响应格式化 | API |
| `SettingsRouter` | LLM 配置 CRUD 路由 | API |
| `ResumeApplicationService` | 编排上传→解析→评估流程 | Application |
| `LLMConfigService` | LLM 配置管理 | Application |
| `Resume` | 聚合根实体 | Domain |
| `ResumeParser` (ABC) | 文件→文本提取 | Infrastructure |
| `ResumeExtractor` (ABC) | 文本→结构化抽取 (LLM) | Infrastructure |
| `ResumeClassifier` (ABC) | Profile→分类标签 | Infrastructure |
| `ResumeEvaluator` (ABC) | Profile→多维度评估 (LLM) | Infrastructure |
| `LLMGateway` | 统一 LLM 调用抽象 | Infrastructure |
| `MinIOStorage` | 文件上传/下载 | Infrastructure |

### 2.3 Pipeline Flow

```
upload file
    │
    ▼
[API] validate format + size → save to MinIO → create resume record (status: uploaded)
    │
    ▼
[Celery] trigger async pipeline
    │
    ├── Step 1: TextExtract
    │   ResumeParser.parse(file) → raw_text
    │   Update status: text_parsed
    │
    ├── Step 2: LLMExtract
    │   ResumeExtractor.extract(raw_text) → sections + facts + profile
    │   Update status: fact_extracted
    │
    ├── Step 3: Classify
    │   ResumeClassifier.classify(profile) → ability_tags + stats
    │   Update status: classified
    │
    └── Step 4: Evaluate
        ResumeEvaluator.evaluate(profile) → evaluation report
        Create resume_evaluation record
```

### 2.4 File Structure

```
backend/
├── main.py                                    [NEW]
├── config.py                                  [NEW]
├── celery_app.py                              [NEW]
├── api/
│   └── v1/
│       ├── __init__.py                        [NEW]
│       ├── router.py                          [NEW]
│       ├── resume.py                          [NEW]
│       ├── settings.py                        [NEW]
│       └── schemas.py                         [NEW] (API request/response)
├── application/
│   ├── resume_service.py                      [NEW]
│   └── llm_config_service.py                  [NEW]
├── domain/
│   └── resume/
│       ├── entities.py                        [MODIFY] (rename entites.py)
│       ├── enums.py                           [MODIFY] (fix import bug)
│       ├── schemas.py                         [MODIFY] (fix typo)
│       ├── services.py                        [MODIFY]
│       └── exceptions.py                      [NEW]
├── infrastructure/
│   ├── db/
│   │   ├── database.py                        [NEW]
│   │   ├── models.py                          [NEW] (SQLAlchemy ORM models)
│   │   └── repositories.py                    [NEW]
│   ├── storage/
│   │   └── minio_client.py                    [NEW]
│   ├── llm/
│   │   ├── gateway.py                         [NEW] (LLM Gateway abstraction)
│   │   ├── providers/
│   │   │   ├── openai_provider.py             [NEW]
│   │   │   ├── anthropic_provider.py          [NEW]
│   │   │   └── base.py                        [NEW]
│   │   └── prompts/
│   │       ├── extraction.py                  [NEW]
│   │       └── evaluation.py                  [NEW]
│   ├── parsers/
│   │   ├── base.py                            [NEW]
│   │   ├── pdf_parser.py                      [NEW]
│   │   ├── docx_parser.py                     [NEW]
│   │   └── text_parser.py                     [NEW]
│   ├── extractors/
│   │   ├── base.py                            [NEW]
│   │   └── llm_extractor.py                   [NEW]
│   ├── classifiers/
│   │   ├── base.py                            [NEW]
│   │   └── rule_classifier.py                 [NEW]
│   ├── evaluators/
│   │   ├── base.py                            [NEW]
│   │   └── llm_evaluator.py                   [NEW]
│   └── crypto/
│       └── encryption.py                      [NEW]
├── tasks/
│   └── resume_tasks.py                        [NEW] (Celery tasks)
├── tests/
│   ├── unit/
│   │   ├── test_parsers.py                    [NEW]
│   │   ├── test_classifiers.py                [NEW]
│   │   └── test_schemas.py                    [NEW]
│   └── integration/
│       ├── test_resume_api.py                 [NEW]
│       └── test_pipeline.py                   [NEW]
├── alembic/
│   ├── env.py                                 [NEW]
│   └── versions/                              [NEW]
├── alembic.ini                                [NEW]
├── pyproject.toml                             [NEW]
├── requirements.txt                           [NEW]
├── Dockerfile                                 [NEW]
└── .env.example                               [NEW]

frontend/
├── index.html                                 [NEW]
├── package.json                               [NEW]
├── vite.config.ts                             [NEW]
├── tsconfig.json                              [NEW]
├── tailwind.config.ts                         [NEW]
├── src/
│   ├── main.tsx                               [NEW]
│   ├── App.tsx                                [NEW]
│   ├── router.tsx                             [NEW]
│   ├── api/
│   │   ├── client.ts                          [NEW]
│   │   ├── resume.ts                          [NEW]
│   │   └── settings.ts                        [NEW]
│   ├── stores/
│   │   ├── resumeStore.ts                     [NEW]
│   │   └── settingsStore.ts                   [NEW]
│   ├── pages/
│   │   ├── UploadPage.tsx                     [NEW]
│   │   ├── ResumeResultPage.tsx               [NEW]
│   │   ├── EvaluationPage.tsx                 [NEW]
│   │   └── SettingsPage.tsx                   [NEW]
│   ├── components/
│   │   ├── Layout.tsx                         [NEW]
│   │   ├── FileUploader.tsx                   [NEW]
│   │   ├── ProfileCard.tsx                    [NEW]
│   │   ├── FactCard.tsx                       [NEW]
│   │   ├── EvidenceBadge.tsx                  [NEW]
│   │   ├── ScoreRadar.tsx                     [NEW]
│   │   ├── ScoreGauge.tsx                     [NEW]
│   │   └── LLMConfigForm.tsx                  [NEW]
│   └── types/
│       ├── resume.ts                          [NEW]
│       └── settings.ts                        [NEW]
└── .env.example                               [NEW]

infra/
└── docker/
    └── docker-compose.yml                     [NEW]
```

### 2.5 Frontend Architecture

#### 2.5.1 Tech Stack

| Layer | Technology | Version | Purpose |
|-------|-----------|---------|---------|
| 构建工具 | Vite | 6.x | 开发服务器 + 打包 |
| 框架 | React | 19.x | UI 框架 |
| 语言 | TypeScript | 5.x | 类型安全 |
| 样式 | Tailwind CSS | 4.x | Utility-first CSS |
| UI 组件库 | Neobrutalism UI | latest | 基于 Shadcn UI 的 Neobrutalism 风格组件 |
| 状态管理 | Zustand | 5.x | 轻量级全局状态 |
| 路由 | React Router | 7.x | 客户端路由 |
| HTTP 客户端 | fetch (原生) | — | API 调用，无额外依赖 |
| 图表 | Recharts | 2.x | 雷达图、条形图（评估报告） |

#### 2.5.2 项目初始化

```bash
# 1. 创建 Vite + React + TypeScript 项目
pnpm create vite frontend --template react-ts
cd frontend

# 2. 安装核心依赖
pnpm add react-router zustand recharts

# 3. 安装 Tailwind CSS
pnpm add -D tailwindcss @tailwindcss/vite

# 4. 初始化 Shadcn UI（Neobrutalism 基础）
pnpm dlx shadcn@latest init
# 选择: CSS variables = Yes, base color = 按需, 路径别名 = @/

# 5. 安装 Neobrutalism UI 组件（按需安装）
pnpm dlx shadcn@latest add https://neobrutalism.dev/r/button.json
pnpm dlx shadcn@latest add https://neobrutalism.dev/r/card.json
pnpm dlx shadcn@latest add https://neobrutalism.dev/r/input.json
pnpm dlx shadcn@latest add https://neobrutalism.dev/r/label.json
pnpm dlx shadcn@latest add https://neobrutalism.dev/r/select.json
pnpm dlx shadcn@latest add https://neobrutalism.dev/r/tabs.json
pnpm dlx shadcn@latest add https://neobrutalism.dev/r/progress.json
pnpm dlx shadcn@latest add https://neobrutalism.dev/r/badge.json
pnpm dlx shadcn@latest add https://neobrutalism.dev/r/dialog.json
pnpm dlx shadcn@latest add https://neobrutalism.dev/r/skeleton.json
pnpm dlx shadcn@latest add https://neobrutalism.dev/r/sonner.json
pnpm dlx shadcn@latest add https://neobrutalism.dev/r/tooltip.json
pnpm dlx shadcn@latest add https://neobrutalism.dev/r/accordion.json
pnpm dlx shadcn@latest add https://neobrutalism.dev/r/alert.json
pnpm dlx shadcn@latest add https://neobrutalism.dev/r/dropdown-menu.json
pnpm dlx shadcn@latest add https://neobrutalism.dev/r/form.json
pnpm dlx shadcn@latest add https://neobrutalism.dev/r/switch.json
pnpm dlx shadcn@latest add https://neobrutalism.dev/r/table.json
```

#### 2.5.3 Neobrutalism 设计特征

Neobrutalism UI 基于 Shadcn UI 二次封装，视觉特征：

| 特征 | 描述 |
|------|------|
| 边框 | 粗实线边框（2-3px），黑色 |
| 阴影 | 硬阴影（offset-x/y，无模糊），产生"悬浮卡片"效果 |
| 圆角 | 微圆角或直角 |
| 配色 | 鲜明、大胆的高饱和度色彩 |
| 排版 | 大字号标题，清晰层级 |
| 交互 | 按钮 hover 时阴影偏移，产生"按压"反馈 |

组件安装后位于 `src/components/ui/`，直接 import 使用：
```tsx
import { Button } from '@/components/ui/button'
import { Card, CardHeader, CardTitle, CardContent, CardFooter } from '@/components/ui/card'
import { Input } from '@/components/ui/input'
import { Badge } from '@/components/ui/badge'
```

#### 2.5.4 路由设计

```tsx
// src/router.tsx
const routes = [
  { path: '/',                   element: <Navigate to="/upload" /> },
  { path: '/upload',             element: <UploadPage /> },
  { path: '/resume/:id',         element: <ResumeResultPage /> },
  { path: '/resume/:id/evaluation', element: <EvaluationPage /> },
  { path: '/settings',           element: <SettingsPage /> },
]
```

#### 2.5.5 状态管理 (Zustand)

```typescript
// src/stores/resumeStore.ts
interface ResumeState {
  currentResumeId: string | null
  status: ResumeStatus | null
  profile: CandidateProfile | null
  evaluation: EvaluationData | null
  isPolling: boolean

  setResumeId: (id: string) => void
  setStatus: (status: ResumeStatus) => void
  setProfile: (profile: CandidateProfile) => void
  setEvaluation: (evaluation: EvaluationData) => void
  startPolling: () => void
  stopPolling: () => void
  reset: () => void
}

// src/stores/settingsStore.ts
interface SettingsState {
  llmConfigs: LLMConfig[]
  activeConfig: LLMConfig | null
  isConfigured: boolean

  fetchConfigs: () => Promise<void>
  saveConfig: (config: LLMConfigCreate) => Promise<void>
  deleteConfig: (id: string) => Promise<void>
  testConnection: (config: LLMTestRequest) => Promise<LLMTestResult>
}
```

#### 2.5.6 API Client

```typescript
// src/api/client.ts
const API_BASE = import.meta.env.VITE_API_BASE || 'http://localhost:8000'

async function request<T>(path: string, options?: RequestInit): Promise<ApiResponse<T>> {
  const res = await fetch(`${API_BASE}${path}`, {
    headers: { 'Content-Type': 'application/json', ...options?.headers },
    ...options,
  })
  return res.json()
}

// src/api/resume.ts
export const resumeApi = {
  upload: (file: File) => {
    const form = new FormData()
    form.append('file', file)
    return request<ResumeUploadData>('/api/v1/resume/upload', { method: 'POST', body: form })
  },
  getDetail: (id: string) => request<ResumeDetail>(`/api/v1/resume/${id}`),
  getStatus: (id: string) => request<ResumeStatusData>(`/api/v1/resume/${id}/status`),
  getEvaluation: (id: string) => request<EvaluationData>(`/api/v1/resume/${id}/evaluation`),
  retry: (id: string) => request<ResumeStatusData>(`/api/v1/resume/${id}/retry`, { method: 'POST' }),
}

// src/api/settings.ts
export const settingsApi = {
  getLLMConfigs: () => request<LLMConfig[]>('/api/v1/settings/llm'),
  createLLMConfig: (data: LLMConfigCreate) => request<LLMConfigData>('/api/v1/settings/llm', { method: 'POST', body: JSON.stringify(data) }),
  updateLLMConfig: (id: string, data: LLMConfigUpdate) => request<LLMConfigData>(`/api/v1/settings/llm/${id}`, { method: 'PUT', body: JSON.stringify(data) }),
  deleteLLMConfig: (id: string) => request<void>(`/api/v1/settings/llm/${id}`, { method: 'DELETE' }),
  testConnection: (data: LLMTestRequest) => request<LLMTestData>('/api/v1/settings/llm/test', { method: 'POST', body: JSON.stringify(data) }),
}
```

#### 2.5.7 页面组件规格

##### Page 1: UploadPage (`/upload`)

| 区域 | Neobrutalism 组件 | 功能 |
|------|-------------------|------|
| 页面标题 | 大字号 `<h1>` + Neobrutalism 风格 | "上传简历" |
| 上传区域 | `Card` + 自定义 `FileUploader` | 拖拽 + 点击上传，虚线边框 |
| 格式提示 | `Alert` | 支持格式 + 大小限制 |
| 上传按钮 | `Button` (default variant) | 确认上传 |
| 进度条 | `Progress` | 上传和解析进度 |
| 状态展示 | `Badge` + `Skeleton` | 解析中 / 已完成 / 失败 |
| 错误提示 | `Sonner` (toast) | 格式错误 / 上传失败 |
| LLM 未配置提示 | `Alert` (warning) + `Button` (link to /settings) | 引导用户先配置 |

```
┌──────────────────────────────────────────────────┐
│  ┌─ Card ─────────────────────────────────────┐  │
│  │           📄 上传简历                        │  │
│  │                                             │  │
│  │   ┌─────────────────────────────────────┐   │  │
│  │   │     拖拽文件到此处                    │   │  │
│  │   │     或点击选择文件                    │   │  │
│  │   │                                     │   │  │
│  │   │  支持 PDF / DOCX / TXT / MD         │   │  │
│  │   │  最大 10MB                          │   │  │
│  │   └─────────────────────────────────────┘   │  │
│  │                                             │  │
│  │   [████████████████░░░░] 75% 解析中...      │  │
│  │                                             │  │
│  │   ┌ Button ────────┐                        │  │
│  │   │   开始上传      │                        │  │
│  │   └────────────────┘                        │  │
│  └─────────────────────────────────────────────┘  │
└──────────────────────────────────────────────────┘
```

**轮询逻辑:**
```
上传成功 → 每 2s 轮询 /status
  → status == "evaluated" → navigate(/resume/:id)
  → status == "failed" → 显示错误 + 重试按钮
  → 超过 3 分钟 → 轮询间隔降为 5s
```

##### Page 2: ResumeResultPage (`/resume/:id`)

| 区域 | Neobrutalism 组件 | 功能 |
|------|-------------------|------|
| 候选人信息 | `Card` + `Badge` | 姓名、联系方式、链接、标签 |
| 内容切换 | `Tabs` | 教育 / 工作 / 项目 / 技能 / 证书 |
| 经历列表 | `Card` (列表) | 每段经历一个卡片 |
| 技能展示 | `Badge` (多个) | 技能标签 + 置信度颜色 |
| Evidence 查看 | `Accordion` / `Tooltip` | 展开显示原文引用 |
| 置信度指示 | `Badge` (variant) | 绿色 ≥0.8 / 黄色 ≥0.5 / 红色 <0.5 |
| 分类标签 | `Badge` (多色) | ability_tags 展示 |
| 加载态 | `Skeleton` | 数据未就绪时显示 |
| 查看评估按钮 | `Button` | 跳转到 /resume/:id/evaluation |

```
┌──────────────────────────────────────────────────────┐
│  ┌─ ProfileCard ──────────────────────────────────┐  │
│  │  张三   📧 zhangsan@email.com   📱 138xxxx     │  │
│  │  [Backend] [Senior] [分布式系统]                  │  │
│  └────────────────────────────────────────────────┘  │
│                                                      │
│  ┌─ Tabs ────────────────────────────────────────┐   │
│  │ [教育] [工作经历] [项目经历] [技能] [证书]      │   │
│  │ ─────────────────────────────────────────────  │   │
│  │ ┌─ Card ──────────────────────────────────┐   │   │
│  │ │  XX 大学 · 计算机科学 · 硕士 · 2018-2021 │   │   │
│  │ │  置信度: [0.95 ✓]                       │   │   │
│  │ │  ▸ 查看原文 Evidence                     │   │   │
│  │ └─────────────────────────────────────────┘   │   │
│  │ ┌─ Card ──────────────────────────────────┐   │   │
│  │ │  YY 大学 · 软件工程 · 本科 · 2014-2018  │   │   │
│  │ └─────────────────────────────────────────┘   │   │
│  └───────────────────────────────────────────────┘   │
│                                                      │
│  ┌ Button ─────────┐                                 │
│  │  查看 AI 评估报告 │                                 │
│  └─────────────────┘                                 │
└──────────────────────────────────────────────────────┘
```

##### Page 3: EvaluationPage (`/resume/:id/evaluation`)

| 区域 | 组件 | 功能 |
|------|------|------|
| 综合评分 | 自定义 `ScoreGauge` (SVG 环形) | 大数字 + 环形进度 |
| 维度评分 | `Recharts RadarChart` 或 `Table` + `Progress` | 8 维度雷达图 / 横向条形 |
| 优势列表 | `Card` + 绿色 `Badge` | 3-5 条优势 + evidence |
| 风险列表 | `Card` + 红色/黄色 `Badge` | 风险项 + severity + evidence |
| 面试建议 | `Accordion` (4 组) | 追问 / 疑似夸大 / 验证方向 / 跳过 |
| Summary | `Alert` (info) | 综合评价文本 |
| 评估中状态 | `Skeleton` + `Progress` (indeterminate) | 等待评估完成 |

```
┌──────────────────────────────────────────────────────┐
│                                                      │
│  ┌─ ScoreGauge ──┐   ┌─ RadarChart ──────────────┐  │
│  │               │   │                            │  │
│  │      85       │   │    技术 ────── 项目        │  │
│  │    ╱────╲     │   │   ╱              ╲        │  │
│  │   Overall     │   │  AI                工程    │  │
│  │               │   │   ╲              ╱        │  │
│  └───────────────┘   │    影响 ────── 架构        │  │
│                      └────────────────────────────┘  │
│                                                      │
│  ┌─ Strengths ─────────────────────────────────────┐ │
│  │ ✅ 大型分布式系统经验 — "负责XX系统百万级QPS..."   │ │
│  │ ✅ 云原生经验丰富 — "主导K8s集群迁移..."         │ │
│  │ ✅ AI Agent 开发经验 — "基于LangChain构建..."    │ │
│  └─────────────────────────────────────────────────┘ │
│                                                      │
│  ┌─ Risks ─────────────────────────────────────────┐ │
│  │ ⚠️ [高] 工作经历存在 6 个月空档 (2022.3-2022.9) │ │
│  │ ⚠️ [中] 项目描述过于笼统，缺少量化指标          │ │
│  └─────────────────────────────────────────────────┘ │
│                                                      │
│  ┌─ Accordion: 面试建议 ───────────────────────────┐ │
│  │ ▸ 值得追问的问题 (5)                            │ │
│  │ ▸ 疑似夸大的地方 (2)                            │ │
│  │ ▸ 建议验证的方向 (3)                            │ │
│  │ ▸ 建议跳过的方向 (1)                            │ │
│  └─────────────────────────────────────────────────┘ │
│                                                      │
│  ┌─ Alert: Summary ───────────────────────────────┐  │
│  │ 适合高级后端岗位，偏工程型，分布式经验较好，      │  │
│  │ AI 能力属于应用层，适合作为二面候选人。            │  │
│  └────────────────────────────────────────────────┘  │
└──────────────────────────────────────────────────────┘
```

##### Page 4: SettingsPage (`/settings`)

| 区域 | Neobrutalism 组件 | 功能 |
|------|-------------------|------|
| 页面标题 | `<h1>` | "AI 模型配置" |
| Provider 选择 | `Select` | OpenAI / Claude / DeepSeek / Custom |
| 模型选择 | `Select` (动态) | 根据 provider 显示对应模型列表 |
| API Key 输入 | `Input` (type=password) + `Button` (eye icon) | 密码输入 + 显示/隐藏切换 |
| Base URL | `Input` | 仅 Custom provider 或代理场景显示 |
| 测试连接 | `Button` (secondary) | 调用 /test → 显示成功/失败 |
| 保存按钮 | `Button` (default) | 保存配置 |
| 已有配置列表 | `Table` 或 `Card` 列表 | 展示已保存的配置，支持编辑/删除 |
| Toast | `Sonner` | 保存成功/失败/测试结果 |

**Provider → 模型映射:**
```typescript
const MODEL_OPTIONS: Record<string, string[]> = {
  openai: ['gpt-4o', 'gpt-4o-mini', 'gpt-4-turbo', 'o3-mini'],
  anthropic: ['claude-sonnet-4-20250514', 'claude-haiku-4-5-20251001', 'claude-opus-4-20250514'],
  deepseek: ['deepseek-chat', 'deepseek-reasoner'],
  custom: [],  // 用户手动填写
}
```

```
┌──────────────────────────────────────────────────────┐
│  AI 模型配置                                          │
│                                                      │
│  ┌─ Card: 新增配置 ──────────────────────────────┐   │
│  │                                                │   │
│  │  Provider     [  OpenAI          ▾ ]           │   │
│  │  Model        [  gpt-4o          ▾ ]           │   │
│  │  API Key      [  ••••••••••••••  👁 ]           │   │
│  │  Base URL     [  (optional)         ]           │   │
│  │                                                │   │
│  │  [ 测试连接 ]   [ 保存配置 ]                    │   │
│  │                                                │   │
│  │  ✅ 连接成功！可用模型: gpt-4o, gpt-4o-mini     │   │
│  └────────────────────────────────────────────────┘   │
│                                                      │
│  ┌─ Table: 已保存配置 ───────────────────────────┐   │
│  │  Provider  │ Model     │ Key      │ Actions   │   │
│  │  OpenAI    │ gpt-4o    │ sk-...4f │ ✏️ 🗑     │   │
│  │  Anthropic │ claude... │ sk-...b2 │ ✏️ 🗑     │   │
│  └────────────────────────────────────────────────┘   │
└──────────────────────────────────────────────────────┘
```

#### 2.5.8 Layout 组件

```tsx
// src/components/Layout.tsx
// 全局 Layout：顶部导航 + 内容区域

// 导航栏组件:
// - Logo / 项目名称 (左侧)
// - 导航链接: 上传简历 (link to /upload)
// - 设置按钮: ⚙️ 图标 (link to /settings)

// 使用 Neobrutalism 的 Button (variant="neutral") 做导航按钮
```

#### 2.5.9 TypeScript Types

```typescript
// src/types/resume.ts
interface ResumeStatus {
  resume_id: string
  status: 'uploaded' | 'text_parsed' | 'fact_extracted' | 'classified' | 'evaluated' | 'failed'
  current_step: string | null
  error: string | null
  completed_steps: string[]
}

interface CandidateProfile {
  identity: Identity
  education: Education[]
  work_experiences: WorkExperience[]
  projects: ProjectExperience[]
  skills: Skill[]
  certificates: Certificate[]
  ability_tags: string[]
  interview_clues: string[]
  risks: string[]
}

interface DimensionScore {
  score: number
  reason: string
  evidence: string
}

interface EvaluationData {
  evaluation_id: string
  overall_score: number
  dimension_scores: Record<string, DimensionScore>
  strengths: { point: string; evidence: string }[]
  risks: { point: string; evidence: string; severity: 'high' | 'medium' | 'low' }[]
  interview_suggestions: {
    worth_asking: string[]
    suspicious: string[]
    verify_direction: string[]
    skip: string[]
  }
  summary: string
  llm_model: string
  created_at: string
}

// src/types/settings.ts
interface LLMConfig {
  id: string
  provider: 'openai' | 'anthropic' | 'deepseek' | 'custom'
  api_key_masked: string
  model_name: string
  base_url: string | null
  is_active: boolean
}

interface LLMConfigCreate {
  provider: string
  api_key: string
  model_name: string
  base_url?: string
}
```

#### 2.5.10 Vite 开发配置

```typescript
// vite.config.ts
export default defineConfig({
  plugins: [react(), tailwindcss()],
  resolve: {
    alias: { '@': path.resolve(__dirname, './src') },
  },
  server: {
    port: 5173,
    proxy: {
      '/api': {
        target: 'http://localhost:8000',
        changeOrigin: true,
      },
    },
  },
})
```

---

## 3. Data Model

### 3.1 Schema Changes

#### Table: `users`

```sql
CREATE TABLE users (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    email VARCHAR(255),
    name VARCHAR(255),
    role VARCHAR(50) DEFAULT 'interviewer',
    created_at TIMESTAMPTZ DEFAULT now(),
    updated_at TIMESTAMPTZ DEFAULT now()
);
```

#### Table: `files`

```sql
CREATE TABLE files (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    original_name VARCHAR(500) NOT NULL,
    storage_path VARCHAR(1000) NOT NULL,
    content_type VARCHAR(100) NOT NULL,
    size_bytes BIGINT NOT NULL,
    sha256_hash VARCHAR(64) NOT NULL,
    page_count INT,
    owner_type VARCHAR(50) NOT NULL DEFAULT 'resume',
    owner_id UUID,
    created_at TIMESTAMPTZ DEFAULT now()
);

CREATE INDEX idx_files_sha256 ON files(sha256_hash);
CREATE INDEX idx_files_owner ON files(owner_type, owner_id);
```

#### Table: `resumes`

```sql
CREATE TABLE resumes (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID REFERENCES users(id),
    file_id UUID REFERENCES files(id),
    status VARCHAR(50) NOT NULL DEFAULT 'uploaded',
    raw_text TEXT,
    parsed_result JSONB,
    parser_version VARCHAR(50),
    parse_error TEXT,
    created_at TIMESTAMPTZ DEFAULT now(),
    updated_at TIMESTAMPTZ DEFAULT now()
);

CREATE INDEX idx_resumes_user ON resumes(user_id);
CREATE INDEX idx_resumes_status ON resumes(status);
```

`parsed_result` JSONB structure:
```json
{
  "sections": [
    {
      "type": "work_experience",
      "content": "...",
      "start_line": 15,
      "end_line": 40
    }
  ],
  "facts": [
    {
      "fact_type": "skill",
      "key": "Redis",
      "value": {"name": "Redis", "category": "cache"},
      "evidence": {
        "source_text": "负责 Redis Cluster 架构设计",
        "page": 1,
        "section": "work_experience",
        "confidence": 0.92
      }
    }
  ],
  "profile": {
    "identity": {...},
    "education": [...],
    "work_experiences": [...],
    "projects": [...],
    "skills": [...],
    "certificates": [...],
    "ability_tags": [...],
    "interview_clues": [...],
    "risks": [...]
  }
}
```

#### Table: `resume_evaluations`

```sql
CREATE TABLE resume_evaluations (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    resume_id UUID NOT NULL REFERENCES resumes(id) ON DELETE CASCADE,
    overall_score FLOAT NOT NULL,
    dimension_scores JSONB NOT NULL,
    strengths JSONB NOT NULL,
    risks JSONB NOT NULL,
    interview_suggestions JSONB NOT NULL,
    summary TEXT NOT NULL,
    llm_model VARCHAR(100),
    llm_provider VARCHAR(50),
    token_usage JSONB,
    created_at TIMESTAMPTZ DEFAULT now()
);

CREATE INDEX idx_resume_evaluations_resume ON resume_evaluations(resume_id);
```

`dimension_scores` structure:
```json
{
  "technical": {"score": 85, "reason": "...", "evidence": "..."},
  "project_quality": {"score": 78, "reason": "...", "evidence": "..."},
  "engineering": {"score": 82, "reason": "...", "evidence": "..."},
  "architecture": {"score": 70, "reason": "...", "evidence": "..."},
  "business_complexity": {"score": 65, "reason": "...", "evidence": "..."},
  "impact": {"score": 60, "reason": "...", "evidence": "..."},
  "growth_potential": {"score": 75, "reason": "...", "evidence": "..."},
  "ai_capability": {"score": 50, "reason": "...", "evidence": "..."}
}
```

#### Table: `llm_configs`

```sql
CREATE TABLE llm_configs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID REFERENCES users(id),
    provider VARCHAR(50) NOT NULL,
    api_key_encrypted TEXT NOT NULL,
    model_name VARCHAR(100) NOT NULL,
    base_url VARCHAR(500),
    is_active BOOLEAN DEFAULT true,
    created_at TIMESTAMPTZ DEFAULT now(),
    updated_at TIMESTAMPTZ DEFAULT now()
);

CREATE INDEX idx_llm_configs_user ON llm_configs(user_id);
```

### 3.2 Entity Definitions

#### Domain Enums (fix existing `enums.py`)

```python
from enum import Enum

class ResumeStatus(str, Enum):
    UPLOADED = "uploaded"
    TEXT_PARSED = "text_parsed"
    FACT_EXTRACTED = "fact_extracted"
    CLASSIFIED = "classified"
    EVALUATED = "evaluated"      # NEW
    FAILED = "failed"

class LLMProvider(str, Enum):
    OPENAI = "openai"
    ANTHROPIC = "anthropic"
    DEEPSEEK = "deepseek"
    CUSTOM = "custom"
```

#### Domain Schemas (fix existing `schemas.py`)

Fix `from typing import List, Optional, Any, Dict` (typo: `Opional` → `Optional`).

Add evaluation schemas:

```python
class DimensionScore(BaseModel):
    score: float = Field(ge=0, le=100)
    reason: str
    evidence: str

class ResumeEvaluation(BaseModel):
    overall_score: float = Field(ge=0, le=100)
    dimension_scores: Dict[str, DimensionScore]
    strengths: List[Dict[str, str]]   # [{point, evidence}]
    risks: List[Dict[str, str]]       # [{point, evidence}]
    interview_suggestions: Dict[str, List[str]]  # {worth_asking, suspicious, verify, skip}
    summary: str
```

### 3.3 ORM Models

```python
# backend/infrastructure/db/models.py

class UserModel(Base):
    __tablename__ = "users"
    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    email: Mapped[Optional[str]]
    name: Mapped[Optional[str]]
    role: Mapped[str] = mapped_column(default="interviewer")

class FileModel(Base):
    __tablename__ = "files"
    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    original_name: Mapped[str]
    storage_path: Mapped[str]
    content_type: Mapped[str]
    size_bytes: Mapped[int]
    sha256_hash: Mapped[str] = mapped_column(index=True)
    page_count: Mapped[Optional[int]]
    owner_type: Mapped[str] = mapped_column(default="resume")
    owner_id: Mapped[Optional[UUID]]

class ResumeModel(Base):
    __tablename__ = "resumes"
    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    user_id: Mapped[Optional[UUID]] = mapped_column(ForeignKey("users.id"))
    file_id: Mapped[Optional[UUID]] = mapped_column(ForeignKey("files.id"))
    status: Mapped[str] = mapped_column(default=ResumeStatus.UPLOADED.value)
    raw_text: Mapped[Optional[str]]
    parsed_result: Mapped[Optional[dict]] = mapped_column(JSONB)
    parser_version: Mapped[Optional[str]]
    parse_error: Mapped[Optional[str]]
    file: Mapped["FileModel"] = relationship()
    evaluations: Mapped[List["ResumeEvaluationModel"]] = relationship(back_populates="resume")

class ResumeEvaluationModel(Base):
    __tablename__ = "resume_evaluations"
    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    resume_id: Mapped[UUID] = mapped_column(ForeignKey("resumes.id", ondelete="CASCADE"))
    overall_score: Mapped[float]
    dimension_scores: Mapped[dict] = mapped_column(JSONB)
    strengths: Mapped[list] = mapped_column(JSONB)
    risks: Mapped[list] = mapped_column(JSONB)
    interview_suggestions: Mapped[dict] = mapped_column(JSONB)
    summary: Mapped[str]
    llm_model: Mapped[Optional[str]]
    llm_provider: Mapped[Optional[str]]
    token_usage: Mapped[Optional[dict]] = mapped_column(JSONB)
    resume: Mapped["ResumeModel"] = relationship(back_populates="evaluations")

class LLMConfigModel(Base):
    __tablename__ = "llm_configs"
    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    user_id: Mapped[Optional[UUID]] = mapped_column(ForeignKey("users.id"))
    provider: Mapped[str]
    api_key_encrypted: Mapped[str]
    model_name: Mapped[str]
    base_url: Mapped[Optional[str]]
    is_active: Mapped[bool] = mapped_column(default=True)
```

### 3.4 Migration Plan

使用 Alembic 管理迁移。

```
alembic revision --autogenerate -m "create_initial_tables"
alembic upgrade head
```

第一版不需要回滚策略——全新建表，无数据迁移风险。

---

## 4. API Design

### 4.1 Endpoints

| Method | Path | Description | Auth | Request | Response |
|--------|------|-------------|------|---------|----------|
| GET | `/api/health` | 健康检查 | No | — | `{"status": "ok"}` |
| POST | `/api/v1/resume/upload` | 上传简历 | No* | multipart/form-data | ResumeUploadResponse |
| GET | `/api/v1/resume/{resume_id}` | 获取解析结果 | No* | — | ResumeDetailResponse |
| GET | `/api/v1/resume/{resume_id}/status` | 查询处理状态 | No* | — | ResumeStatusResponse |
| GET | `/api/v1/resume/{resume_id}/evaluation` | 获取评估报告 | No* | — | EvaluationResponse |
| POST | `/api/v1/resume/{resume_id}/retry` | 重试失败步骤 | No* | — | ResumeStatusResponse |
| GET | `/api/v1/settings/llm` | 获取 LLM 配置 | No* | — | LLMConfigListResponse |
| POST | `/api/v1/settings/llm` | 创建 LLM 配置 | No* | LLMConfigCreateRequest | LLMConfigResponse |
| PUT | `/api/v1/settings/llm/{id}` | 更新 LLM 配置 | No* | LLMConfigUpdateRequest | LLMConfigResponse |
| DELETE | `/api/v1/settings/llm/{id}` | 删除 LLM 配置 | No* | — | `{"code": 0}` |
| POST | `/api/v1/settings/llm/test` | 测试 LLM 连接 | No* | LLMTestRequest | LLMTestResponse |

> *No Auth — 第一版无用户认证系统，使用硬编码 user_id 或请求头 `X-User-Id`。

### 4.2 Request/Response Schemas

#### Resume Upload

```python
# Request: multipart/form-data
# Field: file (UploadFile), required

# Response
class ResumeUploadResponse(BaseModel):
    code: int = 0
    message: str = "success"
    data: ResumeUploadData

class ResumeUploadData(BaseModel):
    resume_id: str
    file_id: str
    status: str   # "uploaded"
```

#### Resume Detail

```python
class ResumeDetailResponse(BaseModel):
    code: int = 0
    message: str = "success"
    data: ResumeDetail

class ResumeDetail(BaseModel):
    resume_id: str
    status: str
    file_name: str
    profile: Optional[CandidateProfile]
    sections: Optional[List[ResumeSection]]
    facts: Optional[List[ResumeFact]]
    created_at: str
```

#### Resume Status

```python
class ResumeStatusResponse(BaseModel):
    code: int = 0
    message: str = "success"
    data: ResumeStatusData

class ResumeStatusData(BaseModel):
    resume_id: str
    status: str                      # uploaded | text_parsed | fact_extracted | classified | evaluated | failed
    current_step: Optional[str]      # 当前正在执行的步骤
    error: Optional[str]             # 失败时的错误信息
    completed_steps: List[str]       # 已完成的步骤列表
```

#### Evaluation

```python
class EvaluationResponse(BaseModel):
    code: int = 0
    message: str = "success"
    data: Optional[EvaluationData]

class EvaluationData(BaseModel):
    evaluation_id: str
    overall_score: float
    dimension_scores: Dict[str, DimensionScore]
    strengths: List[StrengthItem]
    risks: List[RiskItem]
    interview_suggestions: InterviewSuggestions
    summary: str
    llm_model: str
    created_at: str

class StrengthItem(BaseModel):
    point: str
    evidence: str

class RiskItem(BaseModel):
    point: str
    evidence: str
    severity: str  # high | medium | low

class InterviewSuggestions(BaseModel):
    worth_asking: List[str]
    suspicious: List[str]
    verify_direction: List[str]
    skip: List[str]
```

#### LLM Config

```python
class LLMConfigCreateRequest(BaseModel):
    provider: str          # openai | anthropic | deepseek | custom
    api_key: str
    model_name: str
    base_url: Optional[str] = None

class LLMConfigResponse(BaseModel):
    code: int = 0
    message: str = "success"
    data: LLMConfigData

class LLMConfigData(BaseModel):
    id: str
    provider: str
    api_key_masked: str    # "sk-...Ab1c"
    model_name: str
    base_url: Optional[str]
    is_active: bool

class LLMTestRequest(BaseModel):
    provider: str
    api_key: str
    model_name: str
    base_url: Optional[str] = None

class LLMTestResponse(BaseModel):
    code: int = 0
    message: str = "success"
    data: LLMTestData

class LLMTestData(BaseModel):
    connected: bool
    models_available: Optional[List[str]]
    error: Optional[str]
```

### 4.3 Error Responses

| Error Code | HTTP Status | Condition | Message |
|------------|-------------|-----------|---------|
| 0 | 200 | 成功 | success |
| 1001 | 400 | 参数错误（格式/大小） | Invalid file format / File too large |
| 1002 | 404 | Resume/Config 不存在 | Resource not found |
| 1003 | 409 | 状态冲突（重复上传） | Resume already exists |
| 1004 | 400 | LLM 配置无效 | Invalid LLM configuration |
| 5001 | 502 | LLM 调用失败 | LLM service error |
| 5002 | 504 | Pipeline 超时 | Processing timeout |

---

## 5. Business Logic

### 5.1 File Upload Flow

```
1. 验证文件格式（扩展名 + MIME type）
2. 验证文件大小 ≤ 10MB
3. 计算 SHA256 hash
4. 查询 files 表是否存在相同 hash
   → 存在: 返回已关联的 resume_id (code: 0, 不是错误)
   → 不存在: 继续
5. 上传至 MinIO: resumes/{user_id}/{uuid}.{ext}
6. 创建 files 记录
7. 创建 resumes 记录 (status: uploaded)
8. 触发 Celery 异步任务 `process_resume_pipeline`
9. 返回 resume_id + file_id
```

### 5.2 Text Extraction

```
Input: file_path (MinIO path), file_type
Output: raw_text, page_count

1. 从 MinIO 下载文件到临时路径
2. 根据 file_type 选择 Parser:
   - .pdf  → PdfResumeParser (PyMuPDF)
   - .docx → DocxResumeParser (python-docx)
   - .txt/.md → TextResumeParser (直接读取)
3. parser.parse(temp_path) → ParsedResumeText
4. 保存 raw_text 到 resumes 表
5. 保存 page_count 到 files 表
6. 更新 status → text_parsed
7. 清理临时文件
```

### 5.3 LLM Structured Extraction

```
Input: raw_text
Output: sections[], facts[], profile (CandidateProfile)

1. 获取用户 LLM 配置（优先用户配置，回退系统默认）
2. 构造 extraction prompt（见 5.6）
3. 调用 LLM Gateway:
   - 使用 JSON Mode / Structured Output
   - 输入: raw_text + extraction prompt
   - 输出: { sections, facts, profile }
4. 解析 LLM 输出，验证符合 schema
5. 保存到 resumes.parsed_result (JSONB)
6. 记录 parser_version, token_usage
7. 更新 status → fact_extracted
```

### 5.4 Resume Classification

```
Input: CandidateProfile
Output: ability_tags[], statistics

Rules (规则优先):
1. 技术方向标签:
   - skills 中包含 backend 关键词 (Java/Go/Python/Node...) → "Backend"
   - skills 中包含 frontend 关键词 (React/Vue/Angular/CSS...) → "Frontend"
   - skills 中包含 AI 关键词 (PyTorch/TensorFlow/LLM/NLP...) → "AI Engineer"
   - skills 中包含 DevOps 关键词 (K8s/Docker/CI-CD/Terraform...) → "DevOps"
   - skills 中包含 Data 关键词 (Spark/Flink/Hadoop/ETL...) → "Data Engineer"

2. 经验等级:
   - 工作年限 0-2 → "Junior"
   - 工作年限 3-5 → "Mid"
   - 工作年限 6-9 → "Senior"
   - 工作年限 10+ → "Staff"
   (工作年限 = max(end_date) - min(start_date) across work_experiences)

3. 行业领域: 从 work_experiences 的公司/行业提取

4. 统计:
   - total_years: 工作年限
   - project_count: 项目数量
   - tech_depth: 技能数量 / 类别覆盖度
   - has_management: 职位含 "Lead"/"Manager"/"Director"/"VP"
```

### 5.5 AI Resume Evaluation

```
Input: CandidateProfile (from parsed_result)
Output: ResumeEvaluation

1. 获取 LLM 配置
2. 构造 evaluation prompt（见 5.7）
3. 调用 LLM:
   - 输入: profile JSON + evaluation prompt
   - 输出: ResumeEvaluation JSON
4. 验证输出 schema
5. 创建 resume_evaluations 记录
6. 更新 resume status → evaluated
```

### 5.6 LLM Extraction Prompt

```python
EXTRACTION_SYSTEM_PROMPT = """你是一名专业的简历分析师。请对以下简历文本进行结构化信息抽取。

要求：
1. 识别简历的各个区块（基本信息、教育背景、工作经历、项目经历、技能、证书等）
2. 从每个区块中提取结构化事实（Facts）
3. 每个 Fact 必须包含原文引用（evidence），标注置信度（0-1）
4. 汇总生成 CandidateProfile

输出严格使用以下 JSON 格式：
{
  "sections": [...],
  "facts": [...],
  "profile": {
    "identity": {...},
    "education": [...],
    "work_experiences": [...],
    "projects": [...],
    "skills": [...],
    "certificates": [...],
    "ability_tags": [],
    "interview_clues": [],
    "risks": []
  }
}

禁止猜测或补充简历中不存在的信息。如果某字段无法从简历中提取，设为 null。"""
```

### 5.7 LLM Evaluation Prompt

```python
EVALUATION_SYSTEM_PROMPT = """你是一名资深技术面试官（10年+经验）。请基于以下候选人画像进行多维度评估。

评估要求：
1. 以真实面试官的视角评分，不要敷衍，不要给安慰分
2. 每个维度给出 0-100 分，附带具体理由和依据
3. 找出候选人的核心优势（3-5 条），附带证据
4. 找出潜在风险（简历空档、职责夸大、技术跨度异常等）
5. 给出面试建议：值得追问的方向、疑似夸大的地方、建议验证的方向

评估维度：
- 技术能力 (technical): 技术栈深度和广度
- 项目质量 (project_quality): 项目复杂度、规模、业务价值
- 工程能力 (engineering): 工程实践、代码质量、测试意识
- 架构能力 (architecture): 系统设计、分布式经验
- 业务复杂度 (business_complexity): 业务理解、领域经验
- 影响力 (impact): 技术影响力、团队贡献
- 成长性 (growth_potential): 学习能力、职业成长轨迹
- AI 能力 (ai_capability): AI/ML 相关经验

输出严格使用 JSON 格式。"""
```

### 5.8 LLM Gateway

```python
class LLMGateway:
    """统一 LLM 调用入口，根据 provider 路由到对应实现。"""

    async def complete(
        self,
        provider: LLMProvider,
        api_key: str,
        model: str,
        messages: list[dict],
        response_format: dict | None = None,
        base_url: str | None = None,
    ) -> LLMResponse:
        match provider:
            case LLMProvider.OPENAI | LLMProvider.DEEPSEEK:
                return await self._call_openai_compatible(api_key, model, messages, response_format, base_url)
            case LLMProvider.ANTHROPIC:
                return await self._call_anthropic(api_key, model, messages, response_format)
            case LLMProvider.CUSTOM:
                return await self._call_openai_compatible(api_key, model, messages, response_format, base_url)

    async def _call_openai_compatible(self, ...):
        """使用 openai SDK，支持自定义 base_url。"""
        client = AsyncOpenAI(api_key=api_key, base_url=base_url)
        response = await client.chat.completions.create(
            model=model,
            messages=messages,
            response_format=response_format,
        )
        return LLMResponse(
            content=response.choices[0].message.content,
            model=response.model,
            usage={"prompt": response.usage.prompt_tokens, "completion": response.usage.completion_tokens},
        )

    async def _call_anthropic(self, ...):
        """使用 anthropic SDK。"""
        client = AsyncAnthropic(api_key=api_key)
        # 将 OpenAI message 格式转换为 Anthropic 格式
        system_msg = next((m["content"] for m in messages if m["role"] == "system"), None)
        user_msgs = [m for m in messages if m["role"] != "system"]
        response = await client.messages.create(
            model=model,
            system=system_msg,
            messages=user_msgs,
            max_tokens=4096,
        )
        return LLMResponse(...)
```

### 5.9 Edge Cases

| Case | Handling |
|------|----------|
| 空白 PDF（扫描件无文字层） | text_extract 返回空文本 → status=failed, error="No text extracted, file may be a scanned image" |
| 超长简历（>50000 字） | LLM 调用前截断到 30000 字（约 10K tokens），记录 warning |
| LLM 返回非法 JSON | 重试 1 次；仍失败则 status=failed |
| 相同 hash 文件重复上传 | 返回已有 resume_id，不重复处理 |
| MinIO 连接失败 | 直接返回 500，不进入 Celery 队列 |
| Celery Worker 重启 | 任务自动重试（max_retries=2），重试间隔 30s |
| 用户未配置 LLM | 使用系统默认配置（环境变量中的 API Key） |

---

## 6. Error Handling

### 6.1 Domain Exceptions

```python
# backend/domain/resume/exceptions.py

class ResumeNotFoundError(Exception): ...
class ResumeParseError(Exception): ...
class UnsupportedFileFormatError(Exception): ...
class FileTooLargeError(Exception): ...
class LLMCallError(Exception): ...
class LLMConfigNotFoundError(Exception): ...
class DuplicateResumeError(Exception):
    def __init__(self, existing_resume_id: str): ...
```

### 6.2 Exception → HTTP Mapping

```python
# API layer exception handler
exception_handlers = {
    UnsupportedFileFormatError: (400, 1001),
    FileTooLargeError: (400, 1001),
    ResumeNotFoundError: (404, 1002),
    LLMConfigNotFoundError: (404, 1002),
    DuplicateResumeError: (200, 0),      # 不是错误，返回已有 ID
    LLMCallError: (502, 5001),
}
```

### 6.3 Celery Task Retry Strategy

```python
@celery_app.task(bind=True, max_retries=2, default_retry_delay=30)
def process_resume_pipeline(self, resume_id: str):
    try:
        # ... pipeline steps
    except LLMCallError as e:
        self.retry(exc=e)
    except Exception as e:
        # mark failed, record error
        update_resume_status(resume_id, "failed", str(e))
```

---

## 7. Security

### 7.1 API Key Encryption

```python
# backend/infrastructure/crypto/encryption.py
from cryptography.fernet import Fernet

class APIKeyEncryptor:
    def __init__(self, key: str):
        self.cipher = Fernet(key.encode())

    def encrypt(self, plaintext: str) -> str:
        return self.cipher.encrypt(plaintext.encode()).decode()

    def decrypt(self, ciphertext: str) -> str:
        return self.cipher.decrypt(ciphertext.encode()).decode()

    @staticmethod
    def mask(api_key: str) -> str:
        if len(api_key) <= 8:
            return "****"
        return api_key[:3] + "..." + api_key[-4:]
```

- 加密密钥通过环境变量 `ENCRYPTION_KEY` 注入
- `ENCRYPTION_KEY` 使用 `Fernet.generate_key()` 生成

### 7.2 Input Validation

- 文件上传: 校验扩展名 + MIME type，限制 10MB
- API Key: 仅在后端加密存储，前端只展示脱敏版本
- SQL 注入: SQLAlchemy ORM 参数化查询
- Path traversal: MinIO 路径使用 UUID，不含用户输入

### 7.3 CORS

```python
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],  # Vite dev server
    allow_methods=["*"],
    allow_headers=["*"],
)
```

---

## 8. Performance

### 8.1 Expected Load

第一版为单用户/小团队使用，无高并发要求。

- 预期 QPS: < 1
- 单次管道耗时: 30-60s（LLM 调用为瓶颈）
- 文件大小: 平均 200KB，最大 10MB

### 8.2 Optimization

- 文件上传: 流式写入 MinIO，不全部加载到内存
- LLM 调用: 异步（Celery），不阻塞 API 响应
- 前端轮询: 轮询间隔 2s，3 分钟后降为 5s
- 数据库: JSONB 字段仅存储，不建 GIN 索引（第一版数据量小）

### 8.3 Timeouts

| Operation | Timeout |
|-----------|---------|
| 文件上传 | 60s (API) |
| 文本提取 | 30s (Celery) |
| LLM 抽取 | 120s (Celery) |
| LLM 评估 | 120s (Celery) |
| LLM 连接测试 | 15s (API) |

---

## 9. Testing Strategy

### 9.1 Unit Tests

| Module | Tests |
|--------|-------|
| `PdfResumeParser` | 解析标准 PDF → 正确文本 + 页数 |
| `DocxResumeParser` | 解析标准 DOCX → 正确文本 |
| `TextResumeParser` | 直接读取 TXT/MD |
| `RuleBasedClassifier` | skills → 正确 tags + 统计 |
| `APIKeyEncryptor` | encrypt → decrypt 往返正确 + mask 脱敏 |
| `ResumeStatus` | 状态枚举值正确 |
| Domain schemas | Pydantic 验证正确性 |

### 9.2 Integration Tests

| Test | Description |
|------|-------------|
| `test_upload_pdf` | 上传 PDF → 返回 resume_id + status=uploaded |
| `test_upload_invalid_format` | 上传 .exe → 返回 1001 |
| `test_upload_too_large` | 上传 >10MB → 返回 1001 |
| `test_upload_duplicate` | 相同文件二次上传 → 返回已有 resume_id |
| `test_get_resume_status` | 查询处理状态返回正确步骤 |
| `test_llm_config_crud` | 创建/读取/更新/删除 LLM 配置 |
| `test_api_key_masked` | GET LLM 配置返回脱敏 Key |

### 9.3 Acceptance Criteria Mapping

| US/FR | Test | Type |
|-------|------|------|
| US-001 | docker-compose up + health check | E2E |
| US-002 / FR-1 | test_upload_pdf, test_upload_invalid | Integration |
| US-003 / FR-3 | test_pdf_parser, test_docx_parser | Unit |
| US-004 / FR-4,5 | test_llm_extraction (mock LLM) | Integration |
| US-005 / FR-6 | test_rule_classifier | Unit |
| US-006 / FR-7 | test_llm_evaluation (mock LLM) | Integration |
| US-007 / FR-8 | test_celery_pipeline | Integration |
| US-011 / FR-11 | test_llm_config_crud | Integration |

---

## 10. Implementation Plan

### 10.1 Phases & Dependencies

```
Phase 1: Foundation (US-001)
  ├─ FastAPI skeleton + config
  ├─ Docker Compose (PG + Redis + MinIO)
  ├─ SQLAlchemy + Alembic + DB tables
  ├─ Celery setup
  └─ Health endpoint

Phase 2: Backend Core (US-002 → US-003 → US-004 → US-005 → US-006)
  ├─ US-002: File upload API + MinIO storage
  ├─ US-003: Text parsers (PDF/DOCX/TXT/MD)
  ├─ US-004: LLM Gateway + Extraction
  ├─ US-005: Rule classifier
  └─ US-006: LLM Evaluator

Phase 3: Pipeline & Config (US-007, US-011)
  ├─ US-007: Celery task chain orchestration
  └─ US-011: LLM Config CRUD API + encryption

Phase 4: Frontend (US-008 → US-012 → US-009 → US-010)
  ├─ US-008: React + Vite init + Upload page
  ├─ US-012: LLM Config page
  ├─ US-009: Parse result page
  └─ US-010: Evaluation report page
```

### 10.2 Issue Mapping

| Issue | SPEC Sections | Priority | Depends On |
|-------|--------------|----------|------------|
| US-001 | 2.4, 3.1, 3.3 | P0 | — |
| US-002 | 4.1, 4.2, 5.1 | P0 | US-001 |
| US-003 | 5.2 | P0 | US-002 |
| US-004 | 5.3, 5.6, 5.8 | P0 | US-003 |
| US-005 | 5.4 | P1 | US-004 |
| US-006 | 5.5, 5.7 | P0 | US-004 |
| US-007 | 5.1 (pipeline), 6.3 | P0 | US-003~006 |
| US-008 | 2.4 (frontend) | P1 | US-002 |
| US-009 | 2.4 (frontend) | P1 | US-004 |
| US-010 | 2.4 (frontend) | P1 | US-006 |
| US-011 | 3.1 (llm_configs), 4.2, 7.1 | P1 | US-001 |
| US-012 | 2.4 (frontend) | P1 | US-011 |

---

## 11. Open Questions & Risks

### 11.1 Unresolved Questions

1. 评估维度权重：第一版等权重（每项同等权重计算 overall），后续可配置
2. 前端暗色模式：第一版不实现，Neobrutalism 默认亮色

### 11.2 Technical Risks

| Risk | Impact | Mitigation |
|------|--------|-----------|
| LLM 输出格式不稳定 | 解析失败率高 | Structured Output / JSON Mode + 重试 + schema 验证 |
| PyMuPDF 对复杂 PDF 解析不佳 | 文本提取不完整 | 加入文本质量检测（字符数 < 阈值则 warn） |
| Anthropic SDK 与 OpenAI 格式差异 | 适配工作量 | LLM Gateway 抽象层封装差异 |
| MinIO 本地开发网络不稳定 | 上传失败 | Docker Compose 统一管理，健康检查 |

### 11.3 Assumptions

- 第一版无需用户认证，使用 `X-User-Id` header 或默认 user_id
- LLM 响应时间 < 60s（单次调用）
- 简历文本长度通常 < 10000 字
- 第一版不需要水平扩展 Celery Worker
