# Draft Template / 草稿模板

This directory contains reusable templates for engineering teams to draft feature requirements before they are converted into formal specs.  
该目录包含可复用的模板，供研发团队在需求正式进入 spec 前编写功能草稿。

## Purpose / 目的

`spec-draft` is a transition stage between incoming product requirements and finalized spec documents. It helps teams organize intent, dependencies, and implementation boundaries before formalization.  
`spec-draft` 是产品需求与正式 spec 之间的过渡阶段，用于在正式化之前梳理目标、依赖关系和实现边界。

## Why This Matters / 为什么需要这个阶段

For a brand-new system, one draft may map directly to one standalone spec.  
对于全新系统，一个 draft 往往可以直接对应一个独立 spec。

For an in-progress system, a new requirement often affects multiple existing domains.  
对于开发中的系统，新需求通常会影响多个既有领域。

For example, adding a single API may also require:  
例如，新增一个接口时，可能同时需要：

- New error codes that may already be referenced by other modules.
- Updates to shared business flows and cross-module handling.
- Alignment with existing context boundaries instead of creating an isolated spec.
- 新增错误码（而这些错误码可能已被其他模块引用）。
- 更新共享业务链路及跨模块处理逻辑。
- 与既有上下文边界对齐，而不是强行拆分为完全独立的 spec。

In these cases, creating a fully independent spec is usually not the best choice. A draft-first process helps determine whether the requirement should be merged into existing specs or introduced as a new one.  
在这类场景下，完全独立新开 spec 往往并不合适。先经过 draft 阶段，可以判断需求应并入现有 spec 还是新建 spec。

## Workflow / 工作流程

1. Engineers convert product requirements into a structured `spec-draft`.
2. `architecture-agent` and `spec-editor` classify the draft, record assumptions, and normalize it using project rules.
3. Stable platform decisions are captured under `design/`.
4. Epic grouping, release order, and dependencies are captured in `specs/roadmap.md`.
5. The draft is normalized into one or more small feature specs under `specs/<SPEC-ID>-<slug>/spec.md`.
6. Implementation, review, and tests stay traceable to the resulting `spec_id`.
1. 研发将产品需求整理为结构化 `spec-draft`。
2. `spec-draft` agent 基于项目规则完成格式化与规范化。
3. spec 与架构相关 agent 协同，把稳定的平台级决策沉淀到 `design/`。
4. Epic、发布顺序和依赖顺序沉淀到 `specs/roadmap.md`。
5. draft 被拆分并规范化为一个或多个 `specs/<SPEC-ID>-<slug>/spec.md`。
6. 实现、测试和评审产物都通过 `spec_id` 保持可追溯。

## Responsibilities / 职责分工

- Engineers: capture requirement intent, business context, and technical constraints in the draft.
- `architecture-agent`: classify impact, identify affected contexts, and decide which design doc, epic, and feature slices the draft belongs to.
- `spec-editor`: enforce format consistency and apply rules for IDs, error codes, response conventions, and related standards.
- `spec-draft`: provide a clear, engineer-oriented intake document before design and feature-spec normalization.
- 研发：在 draft 中明确需求意图、业务上下文与技术约束。
- `architecture-agent`：判断影响面、识别上下文边界，并决定 draft 应归属哪个 design、epic 和 feature spec。
- `spec-editor`：统一格式与排版，并应用规则生成符合项目规范的 ID、错误码、响应处理等内容。
- `spec-draft`：作为面向研发的 intake 文档，提升后续设计文档与 feature spec 产出的准确度与效率。
