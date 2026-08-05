# Backend Project Skeleton + Docker Compose

## Description

搭建 FastAPI 项目骨架和基础设施。初始化 DDD 分层目录结构，配置 Docker Compose（PostgreSQL 16 + Redis 7 + MinIO），配置 Celery Worker，提供健康检查端点。这是所有后续 Issue 的基础。

PRD Reference: US-001
SPEC Reference: Section 2.2, 2.4

## Acceptance Criteria

- [ ] FastAPI 项目初始化，`backend/main.py` 作为入口
- [ ] 目录结构符合 `design/coding-guidelines.md` 的 DDD 分层（api/application/domain/infrastructure）
- [ ] `backend/config.py` 统一管理配置，通过环境变量注入（DATABASE_URL, REDIS_URL, MINIO_ENDPOINT 等）
- [ ] `backend/.env.example` 列出所有环境变量
- [ ] Docker Compose 配置：PostgreSQL 16 (5432) + Redis 7 (6379) + MinIO (9000)
- [ ] MinIO bucket `resumes` 自动创建（通过 init script 或启动命令）
- [ ] `backend/celery_app.py` 配置 Celery + Redis broker，Worker 可启动
- [ ] `GET /api/health` 返回 `{"status": "ok"}`
- [ ] CORS 中间件配置，允许 `http://localhost:5173`
- [ ] `backend/pyproject.toml` 或 `requirements.txt` 列出所有依赖
- [ ] `docker compose up` 可一键启动所有基础服务
- [ ] 修复 `backend/domain/resume/enums.py` 中 `from enum import enum` → `from enum import Enum`
- [ ] 修复 `backend/domain/resume/schemas.py` 中 `Opional` → `Optional`
- [ ] 重命名 `backend/domain/resume/entites.py` → `entities.py`

## Dependencies

None

## Type

infra

## Priority

P0
