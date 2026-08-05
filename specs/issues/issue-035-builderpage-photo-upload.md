# BuilderPage 照片上传/背景选择/预览确认（四态）

## Description

前端 BuilderPage 增加照片模块：上传生活照 → 选择背景色（白/蓝/红）→ 展示处理前后对比预览 → 确认采用或重新上传 → 移除照片。覆盖空、加载、成功、失败四态；501（imaging 未安装）与 422（未检测到人脸）给出明确可操作的提示文案。

PRD Reference: tasks/prd-resume-toolchain-increments.md US-004 / FR-9, FR-10
SPEC Reference: specs/RIP-004-resume-builder/spec.md「API 设计」

## Acceptance Criteria

- [x] 上传控件限制 jpg/png、≤10MB，前端先行校验并提示
- [x] 背景色选择（white/blue/red），调用 `POST /{draft_id}/photo`
- [x] 处理结果原图/成品对比预览；降级（`background_replaced=false`）时展示 `degraded_reason` 提示
- [x] 确认采用（PUT confirm）后简历预览区显示头像；支持移除（DELETE）与重新上传
- [x] 四态齐全：空（未上传）/ 加载（处理中）/ 成功 / 失败（400/422/501 差异化文案）
- [x] 浏览器实际验证完整流程（上传→预览→确认→导出 PDF 含照片；因 imaging 依赖不可安装，成功链路经 API 注入照片对象验证，501 失败态真实实测）
- [x] Lint（oxlint）/ tsc 通过

> Shipped: PR #14（squash 入 main 81b01a6）

## Dependencies

Issue #33, Issue #34

## Type

frontend

## Priority

medium
