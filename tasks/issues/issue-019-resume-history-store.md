# Resume History Store (localStorage)

## Description

新增基于浏览器 localStorage 的简历历史 store：上传成功后写入记录，供"我的简历"页读取。按 resume_id 去重，最多保留 10 条，轮询状态时同步更新。

PRD Reference: US-B1 (tasks/prd-llm-gate-and-my-resumes.md)

## Acceptance Criteria

- [ ] 新增 `resumeHistory` store（参照 `frontend/src/stores/resumeStore.ts`），封装读/写/删/去重逻辑并与 localStorage 同步
- [ ] localStorage key 为 `myResumes`，value 为 JSON 数组，元素含：`resume_id`、`file_name`、`uploaded_at`(ISO)、`status`
- [ ] 上传成功后（`UploadPage` 拿到 `resume_id` 时）写入记录
- [ ] 轮询状态更新时同步刷新本地记录的 `status`
- [ ] 按 `resume_id` 去重；重复上传（相同 resume_id）时更新既有记录而非新增
- [ ] 写入时若总数超过 10 条，按 `uploaded_at` 自动丢弃最早记录
- [ ] Typecheck 通过

## Dependencies

None

## Type

frontend

## Priority

P1
