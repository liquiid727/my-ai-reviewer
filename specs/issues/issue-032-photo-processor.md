# 照片处理器：人脸裁剪 + 换底 + 增强

## Description

Resume Builder 目前只能产出纯文字简历。新增本地照片处理器：用户上传生活照，自动完成人脸检测、一寸比例裁剪、rembg 抠图换底（白/蓝/红）、画质温和增强，输出规范证件照 PNG。全程本地处理，照片不发送第三方服务。

PRD Reference: tasks/prd-resume-toolchain-increments.md US-001 / FR-1~3, FR-14
SPEC Reference: specs/RIP-004-resume-builder/spec.md「核心算法（process_photo）」「设计决策」

## Acceptance Criteria

- [x] 新增 `backend/infrastructure/imaging/photo_processor.py`：`process_photo(data, bg_color) -> ProcessedPhoto`
- [x] 流程：解码校验（EXIF 矫正）→ Haar 人脸检测 → 一寸裁剪（295×413，人脸占高约 40%、头顶留白约 7%）→ rembg 抠图 → 换底（white=#FFFFFF / blue=#438EDB / red=#D43D3D）→ 增强（亮度 1.05/对比度 1.05/锐化 1.1）→ PNG
- [x] 无人脸 → 抛 `FaceNotFoundError`；多张人脸 → 取面积最大者；解码失败 → `ImageDecodeError`
- [x] 抠图失败 → 降级"仅裁剪+增强"，`background_replaced=False` + `degraded_reason`
- [x] 依赖写入 `backend/pyproject.toml` 可选分组 `[imaging]`（opencv-python-headless + rembg）
- [x] 单测：人脸/无人脸/多人脸/降级四路径（fixture 存 `tests/fixtures/photos/`，合成图 + monkeypatch 接缝）
- [x] Lint（ruff）/ mypy 通过

> Shipped: PR #11（squash 入 main `737fa28`）；实现笔记 docs/issue#0032.html

## Dependencies

None

## Type

backend

## Priority

high
