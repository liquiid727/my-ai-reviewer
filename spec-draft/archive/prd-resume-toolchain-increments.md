# PRD: Resume 工具链增量（照片美化 / JD 抽取 / TXT 编码兜底）

> **Source**: `docs/prd/resume-builder.md`（方向性文档）§3.5、`tasks/prd-parser.md` §4/§8
> **关联 Spec**: `specs/RIP-004-resume-builder/`（照片美化）、`specs/RIP-003-jd-matching/`（JD 抽取）、`specs/RIP-001-resume-multiformat-parsers/`（TXT 编码）

## Introduction

简历工具链（解析 → 拆解 → 制作 → 匹配）主链路已实现并通过单测，本 PRD 覆盖三项经代码核对确认的真实待开发增量：

1. **证件照美化**：Resume Builder 目前只能产出纯文字简历，用户需要上传照片并得到规范化证件照（裁剪、换底、增强），嵌入简历模板导出。
2. **LLM JD 抽取器**：`POST /jd` 目前要求调用方手工传入 `required_skills`，真实用户只会粘贴 JD 原文——需要 LLM 自动从原文抽取技能要求。
3. **TXT 编码兜底**：`TextResumeParser` 仅支持 utf-8，上传 GBK 等编码的 txt/md 简历会解析失败。

## Goals

- 用户上传任意含人脸照片，10 秒内获得白/蓝/红底一寸证件照，可嵌入三套模板并导出 PDF
- 用户仅粘贴 JD 原文即可完成创建与匹配，无需手填技能列表
- GBK / GB18030 / Big5 编码的 txt/md 简历上传后解析成功率与 utf-8 一致
- 全部处理本地完成，照片与简历内容不发送第三方服务（LLM 网关除外，且不发送照片）

## User Stories

### US-001: 照片处理器（人脸裁剪 + 换底 + 增强）
**Description:** As a 求职者, I want 上传生活照后自动得到规范证件照 so that 不用另外花钱拍照/修图。

**Acceptance Criteria:**
- [ ] 新增 `backend/infrastructure/imaging/photo_processor.py`，`process_photo(data, bg_color) -> ProcessedPhoto`
- [ ] 流程：解码校验 → 人脸检测（OpenCV Haar）→ 一寸比例裁剪（295×413，人脸居中、头顶留白约 7%）→ rembg 抠图 → 填充背景（white/blue/red）→ 亮度/对比度/锐化温和增强 → 输出 PNG
- [ ] 无人脸 → 抛 `FaceNotFoundError`；检测到多张人脸 → 取面积最大者
- [ ] 抠图失败 → 降级返回"仅裁剪+增强"，`ProcessedPhoto.background_replaced=False` 并携带降级原因
- [ ] 单测：含人脸样张、无人脸样张、多人脸样张（fixture 存 `tests/fixtures/photos/`）
- [ ] Lint（ruff）/ mypy 通过

### US-002: 照片 API 与草稿集成
**Description:** As a 求职者, I want 在简历草稿里上传、确认、移除照片 so that 照片成为草稿的一部分随简历导出。

**Acceptance Criteria:**
- [ ] `POST /api/v1/resume-builder/{draft_id}/photo`：multipart 上传，query `bg_color`（默认 white）；非 jpg/png 或 >10MB → HTTP 400 明确错误
- [ ] 处理成功 → 原图与结果分别写 MinIO，返回两者预览 URL + 处理元信息（是否换底、降级原因）
- [ ] 无人脸 → HTTP 422 + `FACE_NOT_FOUND` 错误码
- [ ] `PUT /{draft_id}/photo/confirm` → 草稿 `identity.photo` 写入结果对象名；`DELETE /{draft_id}/photo` → 清除字段（MinIO 对象保留，可追溯）
- [ ] 单测覆盖上传 / 确认 / 删除 / 400 / 422 五条路径
- [ ] Lint / mypy 通过

### US-003: 模板头像渲染与 PDF 内联
**Description:** As a 求职者, I want 选任意模板都能正确展示照片 so that 导出的 PDF 是完整可投递的简历。

**Acceptance Criteria:**
- [ ] classic / modern / compact 三套 Jinja2 模板支持头像位（姓名区右侧）；`identity.photo` 为空时布局不留白、不回归
- [ ] 导出 PDF 时照片以 data URI 内联（从 MinIO 读取），无外链请求
- [ ] 自动一页逻辑对带照片草稿不回归（`test_one_page_logic.py` 扩展带照片用例）
- [ ] 渲染快照单测：三模板 × 有/无照片共 6 种组合
- [ ] Lint / mypy 通过

### US-004: 前端照片上传与预览确认
**Description:** As a 求职者, I want 在 Builder 页上传照片、选背景色、对比预览后确认 so that 所见即所得。

**Acceptance Criteria:**
- [ ] BuilderPage 新增照片卡片：上传按钮、背景色三选（白/蓝/红）、原图与结果对照预览、确认/重新处理/移除操作
- [ ] 四态齐全——Empty：占位引导；Loading：处理中骨架；Success：对照预览；Failure：错误原因（无人脸/超限/格式）+ 重试入口
- [ ] 确认后草稿预览与导出 PDF 均含照片
- [ ] Typecheck（tsc）/ oxlint 通过
- [ ] Verify in browser using dev-browser skill

### US-005: LLM JD 抽取器
**Description:** As a 招聘方/求职者, I want 粘贴 JD 原文即可自动识别技能要求 so that 不需要手工整理技能列表。

**Acceptance Criteria:**
- [ ] 新增 `backend/infrastructure/extractors/jd_extractor.py`：LLM 从 `raw_text` 抽取 `required_skills`（含 critical 标记）、`responsibilities`、`seniority`，Pydantic 结构化输出
- [ ] 抽取结果含 evidence（原文片段），与 Fact 体系口径一致
- [ ] LLM 不可用/输出不合法 → 抛明确异常，不产生半成品数据
- [ ] 单测：mock LLM 网关，覆盖正常抽取 / 输出格式异常两条路径
- [ ] Lint / mypy 通过

### US-006: POST /jd 自动抽取集成
**Description:** As a API 调用方, I want 创建 JD 时未传技能列表则自动抽取 so that 前端只需要一个文本框。

**Acceptance Criteria:**
- [ ] `POST /api/v1/jd`：`required_skills` 为空且 `raw_text` 非空 → 调用 jd_extractor 自动抽取；显式传入 `required_skills` → 跳过抽取（保持向后兼容）
- [ ] 抽取结果（含 responsibilities / seniority）写入 `job_descriptions`（Alembic 迁移补充字段）
- [ ] 抽取失败 → HTTP 502 + `JD_EXTRACTION_FAILED`，JD 不落库
- [ ] 响应体标记 `extraction_source: "llm" | "manual"`
- [ ] 单测：自动抽取 / 手动传入 / 抽取失败三条路径
- [ ] Lint / mypy 通过

### US-007: TXT/MD 编码兜底
**Description:** As a 求职者, I want GBK 等编码的 txt/md 简历也能正常解析 so that 不因文件编码问题上传失败。

**Acceptance Criteria:**
- [ ] `TextResumeParser` / `MarkdownResumeParser` 读取失败时按 `charset-normalizer` 探测编码重读；仍失败 → `errors="replace"` 尽力解码并记 warning
- [ ] 单测：utf-8 / GBK / GB18030 fixture 样本解析结果一致
- [ ] `domain/resume/parse.md` 同步更新为当前 6 格式解析器的真实设计（清理旧版笔记）
- [ ] Lint / mypy 通过

## Functional Requirements

- FR-1: 系统必须提供 `process_photo` 本地照片处理能力：人脸检测、一寸裁剪、背景替换（白/蓝/红）、画质增强
- FR-2: 系统必须在照片无人脸时返回 `FACE_NOT_FOUND` 错误（API 层 HTTP 422）
- FR-3: 系统必须在抠图失败时降级为"仅裁剪+增强"并明确标记降级原因
- FR-4: 系统必须将照片原图与处理结果分别持久化到 MinIO
- FR-5: 系统必须仅在用户确认后才将照片写入草稿 `identity.photo`
- FR-6: 系统必须在三套模板中支持头像渲染，且无照片时布局不留白
- FR-7: 系统必须在导出 PDF 时将照片以 data URI 内联
- FR-8: 系统必须拒绝非 jpg/png 或超过 10MB 的照片上传（HTTP 400）
- FR-9: 系统必须在 `POST /jd` 未传 `required_skills` 时通过 LLM 从原文自动抽取技能要求
- FR-10: 系统必须为 LLM 抽取的每项技能保存 evidence 原文片段
- FR-11: 系统必须在 JD 抽取失败时返回 `JD_EXTRACTION_FAILED` 且不落库半成品
- FR-12: 系统必须在显式传入 `required_skills` 时跳过 LLM 抽取（向后兼容）
- FR-13: 系统必须对非 utf-8 编码的 txt/md 文件进行编码探测兜底解析
- FR-14: 系统必须保证照片处理全程本地完成，不向第三方服务发送照片数据

## Non-Goals

- 不做美颜级人脸修饰（磨皮/瘦脸），仅证件照规范化
- 不做照片背景自定义颜色（仅白/蓝/红三色）
- 不做 JD 前端输入与匹配结果展示页（RIP-003 T6 另行排期）
- 不做面试应对准备与面试知识库（见 `docs/prd/resume-builder.md` §5，下一阶段）
- 不做 OCR 图片简历解析（issue-030 另行跟踪）

## Technical Considerations

- 照片处理：`opencv-python-headless`（Haar cascade，免模型下载）+ `rembg`（onnxruntime 本地推理）+ `Pillow.ImageEnhance`；依赖体积较大，写入 `backend/pyproject.toml` 可选分组 `[imaging]`，未安装时照片 API 返回 501 并提示
- rembg 首次运行会下载 u2net 模型（约 170MB）——部署文档需注明预热步骤 [Assumption: 允许构建期预下载]
- JD 抽取复用现有 `LLMGateway`（与 `llm_extractor.py` 同模式），失败语义与简历抽取一致
- 编码探测用 `charset-normalizer`（纯 Python，pip 生态默认已随 requests 安装）
- `job_descriptions` 补充字段（responsibilities / seniority / extraction_source）需一条新 Alembic 迁移

## Success Metrics

- 含人脸照片处理成功率 ≥ 95%（样张集验证），单张处理耗时 ≤ 10s
- 仅粘贴 JD 原文创建 → 匹配全流程零手工字段输入
- GBK/GB18030 txt 简历解析成功率与 utf-8 持平
- 现有 75 个单测零回归，新增单测覆盖上述全部验收路径

## Open Questions

- 照片是否需要支持自定义裁剪框（用户手动微调）？[当前假设：不需要，自动裁剪 + 不满意可重传]
- rembg 模型体积对部署镜像的影响是否可接受？如不可接受，是否照片美化独立为可选 sidecar 服务？
- JD 抽取的 seniority 枚举口径（初级/中级/高级/专家？）需与后续面试难度体系对齐 [Assumption: 先用 junior/mid/senior/expert 四档]
