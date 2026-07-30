# 模板头像渲染与 PDF data URI 内联

## Description

三套 Jinja2 模板（classic / modern / compact）目前不渲染照片。为各模板增加头像区块：草稿 `identity.photo` 存在时渲染，不存在时布局保持现状（无占位空洞）。PDF 导出时照片从 MinIO 读取并以 base64 data URI 内联，保证 Playwright 离线打印可用，且不破坏 4 档密度自动一页逻辑。

PRD Reference: tasks/prd-resume-toolchain-increments.md US-003 / FR-6, FR-7
SPEC Reference: specs/RIP-004-resume-builder/spec.md「模板渲染」

## Acceptance Criteria

- [ ] classic / modern / compact 三套模板均支持头像区块（位置随模板风格，295:413 比例展示）
- [ ] `identity.photo` 为空时模板渲染结果与现状一致（回归单测保证）
- [ ] PDF 导出：MinIO 读取照片 → base64 data URI 内联进 HTML，无外部网络请求
- [ ] 带照片场景下 4 档密度自动一页逻辑仍正确（1123px 阈值判定不回归）
- [ ] 单测：有照片/无照片 × 3 模板渲染快照；PDF 导出含照片路径
- [ ] Lint / mypy 通过

## Dependencies

Issue #33

## Type

backend

## Priority

high
