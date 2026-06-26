# Frontend Skill

适用于 Next.js 前端开发任务（Phase 1 暂不涉及，预留）。

---

## 技术栈

- Next.js 14+（App Router）
- TypeScript
- Tailwind CSS
- ShadcnUI（组件库）

---

## API 调用规范

```typescript
// 统一 fetch 封装
const res = await fetch('/api/v1/interview/create', {
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify({ resume_id, jd_text }),
})
const data = await res.json()
// data.code === 0 表示成功
```

---

## 核心页面

```text
/interview/new        创建面试（上传简历 + 输入 JD）
/interview/[id]       面试进行中（问答界面）
/interview/[id]/report 面试报告
```

---

## 注意

Phase 1 优先完成后端 API，前端仅用 Postman / curl 验收。
