.PHONY: help infra infra-down db-migrate \
       backend backend-worker frontend \
       dev dev-stop install lint test clean

help: ## 显示所有可用命令
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | \
		awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-18s\033[0m %s\n", $$1, $$2}'

# ── 基础设施 ─────────────────────────────────────

infra: ## 启动 Postgres + Redis + MinIO
	docker compose up -d

infra-down: ## 停止基础设施
	docker compose down

db-migrate: ## 运行数据库迁移
	cd backend && uv run alembic -c ../alembic.ini upgrade head

# ── 后端 ─────────────────────────────────────────

backend: ## 启动 FastAPI 后端 (port 8000)
	cd backend && uv run uvicorn backend.main:app --reload --host 0.0.0.0 --port 8000

backend-worker: ## 启动 Celery worker
	cd backend && uv run celery -A backend.celery_app:celery worker --loglevel=info

# ── 前端 ─────────────────────────────────────────

frontend: ## 启动 Vite 前端 (port 5173)
	cd frontend && pnpm dev

# ── 组合命令 ─────────────────────────────────────

dev: ## 启动全部服务 (infra + backend + frontend)
	@echo "启动基础设施..."
	docker compose up -d
	@echo "等待服务就绪..."
	@sleep 3
	@echo "启动后端和前端 (Ctrl+C 停止)..."
	@trap 'kill 0' INT; \
		(cd backend && uv run uvicorn backend.main:app --reload --host 0.0.0.0 --port 8000) & \
		(cd frontend && pnpm dev) & \
		wait

dev-stop: ## 停止所有服务
	docker compose down
	@-pkill -f "uvicorn backend.main:app" 2>/dev/null || true
	@-pkill -f "vite" 2>/dev/null || true

# ── 开发工具 ─────────────────────────────────────

install: ## 安装前后端依赖
	cd backend && uv sync
	cd frontend && pnpm install

lint: ## 运行 lint 检查
	cd backend && uv run ruff check .
	cd frontend && pnpm lint

test: ## 运行后端测试
	cd backend && uv run pytest

clean: ## 清理构建产物
	rm -rf frontend/dist
	find backend -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
