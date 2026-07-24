SHELL := /bin/bash

BACKEND_HOST ?= 0.0.0.0
BACKEND_PORT ?= 8000
FRONTEND_HOST ?= 0.0.0.0
FRONTEND_PORT ?= 5173

# ── 颜色与符号 ─────────────────────────────────────
RESET   := \033[0m
BOLD    := \033[1m
GREEN   := \033[1;32m
CYAN    := \033[1;36m
YELLOW  := \033[1;33m
PURPLE  := \033[1;35m
BLUE    := \033[1;34m
RED     := \033[1;31m

OK      := ✅
DONE    := 🎉
STAR    := 🚀
GEAR    := ⚙️
BRAIN   := 🧠
ART     := 🎨
FIRE    := 🔥

# 成功输出宏：在 recipe 中通过 $(call ok,消息) 调用
define ok
	@printf "$(GREEN)$(OK) %s$(RESET)\n" "$(1)"
endef

# 运行命令定义
BACKEND_RUN = PYTHONPATH=. uv run --project backend uvicorn backend.main:app --host $(BACKEND_HOST) --port $(BACKEND_PORT)
BACKEND_HOT = $(BACKEND_RUN) --reload
WORKER_RUN = PYTHONPATH=. uv run --project backend celery -A backend.celery_app:celery worker --loglevel=info
FRONTEND_BUILD = cd frontend && pnpm build
FRONTEND_RUN = cd frontend && pnpm preview --host $(FRONTEND_HOST) --port $(FRONTEND_PORT)
FRONTEND_HOT = cd frontend && pnpm dev --host $(FRONTEND_HOST) --port $(FRONTEND_PORT)

.PHONY: help setup infra infra-down db-migrate \
       start start-backend start-worker start-frontend \
       hot hot-backend hot-frontend \
       backend backend-worker frontend \
       dev stop dev-stop install lint test clean

help: ## 显示所有可用命令
	@printf "\n$(PURPLE)$(STAR)  AI Reviewer Make Console$(RESET)\n"
	@printf "    $(BRAIN) backend: http://localhost:%s  $(ART) frontend: http://localhost:%s\n\n" "$(BACKEND_PORT)" "$(FRONTEND_PORT)"
	@grep -E '^[a-zA-Z_-]+:.*?## ' $(MAKEFILE_LIST) | \
		awk 'BEGIN {FS = ":.*## "}; {printf "  $(STAR) \033[36m%-18s\033[0m %s\n", $$1, $$2}'

# ── 初始化 ─────────────────────────────────────────

setup: ## 一键初始化项目 (新机器首次运行)
	bash scripts/setup.sh
	$(call ok,项目初始化完成)

# ── 基础设施 ─────────────────────────────────────

infra: ## 启动 Postgres + Redis + MinIO
	docker compose up -d
	$(call ok,基础设施已启动 (Postgres/Redis/MinIO))

infra-down: ## 停止基础设施
	docker compose down
	$(call ok,基础设施已停止)

db-migrate: ## 运行数据库迁移
	PYTHONPATH=. uv run --project backend alembic -c alembic.ini upgrade head
	$(call ok,数据库迁移完成)

# ── 后端 ─────────────────────────────────────────

start-backend: ## 🧠 启动 FastAPI 后端 (无热编译)
	@printf "$(PURPLE)$(BRAIN) 启动 FastAPI 后端 -> http://localhost:$(BACKEND_PORT)$(RESET)\n"
	@trap 'printf "\n$(RED)🛑 后端已停止$(RESET)\n"; kill 0' INT TERM; \
		($(BACKEND_RUN)) & \
		{ for i in $$(seq 1 40); do \
			if curl -sf http://localhost:$(BACKEND_PORT)/api/health >/dev/null 2>&1; then \
				printf "$(GREEN)$(OK) 后端已就绪 -> http://localhost:$(BACKEND_PORT)/api/health$(RESET)\n"; break; \
			fi; sleep 1; \
		done; }; \
		wait

hot-backend: ## 🔥 启动 FastAPI 后端热编译
	@printf "$(PURPLE)$(FIRE) 启动 FastAPI 后端热编译 -> http://localhost:$(BACKEND_PORT)$(RESET)\n"
	@trap 'printf "\n$(RED)🛑 后端已停止$(RESET)\n"; kill 0' INT TERM; \
		($(BACKEND_HOT)) & \
		{ for i in $$(seq 1 40); do \
			if curl -sf http://localhost:$(BACKEND_PORT)/api/health >/dev/null 2>&1; then \
				printf "$(GREEN)$(OK) 后端热编译已就绪 -> http://localhost:$(BACKEND_PORT)/api/health$(RESET)\n"; break; \
			fi; sleep 1; \
		done; }; \
		wait

start-worker: ## ⚙️ 启动 Celery worker
	@printf "$(YELLOW)$(GEAR) 启动 Celery worker$(RESET)\n"
	@trap 'printf "\n$(RED)🛑 Worker 已停止$(RESET)\n"; kill 0' INT TERM; \
		$(WORKER_RUN)

backend: hot-backend ## 🔥 后端热编译快捷入口

backend-worker: start-worker ## ⚙️ Worker 快捷入口

# ── 前端 ─────────────────────────────────────────

start-frontend: ## 🎨 构建并启动 Vite preview (无热编译)
	@printf "$(BLUE)$(ART) 构建并启动前端 preview -> http://localhost:$(FRONTEND_PORT)$(RESET)\n"
	$(FRONTEND_BUILD)
	$(call ok,前端构建完成)
	@trap 'printf "\n$(RED)🛑 前端已停止$(RESET)\n"; kill 0' INT TERM; \
		($(FRONTEND_RUN)) & \
		{ for i in $$(seq 1 40); do \
			if curl -sf http://localhost:$(FRONTEND_PORT)/ >/dev/null 2>&1; then \
				printf "$(GREEN)$(OK) 前端已就绪 -> http://localhost:$(FRONTEND_PORT)$(RESET)\n"; break; \
			fi; sleep 1; \
		done; }; \
		wait

hot-frontend: ## ⚡ 启动 Vite 前端热编译
	@printf "$(BLUE)⚡ 启动 Vite 前端 HMR -> http://localhost:$(FRONTEND_PORT)$(RESET)\n"
	@trap 'printf "\n$(RED)🛑 前端已停止$(RESET)\n"; kill 0' INT TERM; \
		($(FRONTEND_HOT)) & \
		{ for i in $$(seq 1 40); do \
			if curl -sf http://localhost:$(FRONTEND_PORT)/ >/dev/null 2>&1; then \
				printf "$(GREEN)$(OK) 前端 HMR 已就绪 -> http://localhost:$(FRONTEND_PORT)$(RESET)\n"; break; \
			fi; sleep 1; \
		done; }; \
		wait

frontend: hot-frontend ## ⚡ 前端热编译快捷入口

# ── 组合命令 ─────────────────────────────────────

start: ## 🎉 启动全部服务 (infra + backend + worker + frontend preview)
	@printf "$(PURPLE)$(DONE) 启动全栈 (start 模式)$(RESET)\n"
	docker compose up -d
	@printf "$(CYAN)⏳ 等待基础设施就绪$(RESET)\n"; sleep 3
	@printf "$(YELLOW)📦 构建前端$(RESET)\n"
	$(FRONTEND_BUILD)
	$(call ok,前端构建完成)
	@printf "$(PURPLE)$(BRAIN) 后端 + $(GEAR) Worker + $(ART) 前端 preview (Ctrl+C 停止)$(RESET)\n"
	@trap 'printf "\n$(RED)🛑 全栈已停止$(RESET)\n"; kill 0' INT TERM; \
		($(BACKEND_RUN)) & \
		($(WORKER_RUN)) & \
		($(FRONTEND_RUN)) & \
		{ for i in $$(seq 1 40); do \
			if curl -sf http://localhost:$(BACKEND_PORT)/api/health >/dev/null 2>&1; then \
				printf "$(GREEN)$(OK) 后端已就绪 -> http://localhost:$(BACKEND_PORT)/api/health$(RESET)\n"; break; \
			fi; sleep 1; \
		done; \
		printf "$(GREEN)$(OK) 全栈启动完成 | 前端 http://localhost:$(FRONTEND_PORT) | 后端 http://localhost:$(BACKEND_PORT)$(RESET)\n"; }; \
		wait

hot: ## 🔥 启动全部服务热编译 (infra + backend reload + worker + frontend HMR)
	@printf "$(PURPLE)$(FIRE) 启动全栈 (hot 模式)$(RESET)\n"
	docker compose up -d
	@printf "$(CYAN)⏳ 等待基础设施就绪$(RESET)\n"; sleep 3
	@printf "$(PURPLE)$(BRAIN) 后端热编译 + $(GEAR) Worker + ⚡ 前端 HMR (Ctrl+C 停止)$(RESET)\n"
	@trap 'printf "\n$(RED)🛑 全栈已停止$(RESET)\n"; kill 0' INT TERM; \
		($(BACKEND_HOT)) & \
		($(WORKER_RUN)) & \
		($(FRONTEND_HOT)) & \
		{ for i in $$(seq 1 40); do \
			if curl -sf http://localhost:$(BACKEND_PORT)/api/health >/dev/null 2>&1; then \
				printf "$(GREEN)$(OK) 后端已就绪 -> http://localhost:$(BACKEND_PORT)/api/health$(RESET)\n"; break; \
			fi; sleep 1; \
		done; \
		printf "$(GREEN)$(OK) 全栈热编译启动完成 | 前端 http://localhost:$(FRONTEND_PORT) | 后端 http://localhost:$(BACKEND_PORT)$(RESET)\n"; }; \
		wait

dev: hot ## 🔥 全量热编译快捷入口

stop: ## 🛑 停止所有服务
	docker compose down
	@-pkill -f "uvicorn backend.main:app" 2>/dev/null || true
	@-pkill -f "celery.*backend" 2>/dev/null || true
	@-pkill -f "vite" 2>/dev/null || true
	$(call ok,所有服务已停止)

dev-stop: stop ## 🛑 停止服务快捷入口

# ── 开发工具 ─────────────────────────────────────

install: ## 安装前后端依赖
	cd backend && uv sync
	cd frontend && pnpm install
	$(call ok,前后端依赖安装完成)

lint: ## 运行 lint 检查
	PYTHONPATH=. uv run --project backend ruff check backend
	cd frontend && pnpm lint
	$(call ok,Lint 检查通过)

test: ## 运行后端测试
	PYTHONPATH=. uv run --project backend pytest backend
	$(call ok,测试通过)

clean: ## 清理构建产物
	rm -rf frontend/dist
	find backend -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
	$(call ok,构建产物已清理)
