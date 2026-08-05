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
BOLT    := ⚡
DB      := 💾
DOCKER  := 🐳
PKG     := 📦
STOP    := 🛑

# 成功输出宏：在 recipe 中通过 $(call ok,消息) 调用
define ok
	@printf "$(GREEN)$(OK) %s$(RESET)\n" "$(1)"
endef

# 运行命令定义
BACKEND_RUN = PYTHONPATH=. uv run --project backend uvicorn backend.main:app --host $(BACKEND_HOST) --port $(BACKEND_PORT)
BACKEND_HOT = $(BACKEND_RUN) --reload
WORKER_RUN = PYTHONPATH=. uv run --project backend celery -A backend.celery_app:celery worker --loglevel=info
BEAT_RUN = PYTHONPATH=. uv run --project backend celery -A backend.celery_app:celery beat --loglevel=info
FRONTEND_BUILD = cd frontend && pnpm build
FRONTEND_RUN = cd frontend && pnpm preview --host $(FRONTEND_HOST) --port $(FRONTEND_PORT)
FRONTEND_HOT = cd frontend && pnpm dev --host $(FRONTEND_HOST) --port $(FRONTEND_PORT)
# Keep each service in its own process group so Ctrl+C can clean up descendants.
DEV_SERVICES = python3 scripts/dev_services.py

.PHONY: help setup install \
       start hot dev \
       backend-up frontend-up \
       infra infra-down db-migrate \
       start-backend hot-backend start-worker start-beat backend backend-worker beat \
       start-frontend hot-frontend frontend \
       stop dev-stop clean \
       lint type-check arch-check \
       test test-unit test-integration test-frontend \
       build ci-fast ci

# ── 帮助 ─────────────────────────────────────────

help: ## 📖 显示所有可用命令（按分组展示）
	@printf "\n$(PURPLE)$(STAR)  AI Reviewer Make Console$(RESET)\n"
	@printf "    $(BRAIN) backend: http://localhost:%s   $(ART) frontend: http://localhost:%s\n" "$(BACKEND_PORT)" "$(FRONTEND_PORT)"
	@awk 'BEGIN {FS = ":.*?## "} \
		/^##@/ { printf "\n\033[1;33m%s\033[0m\n", substr($$0, 5); next } \
		/^[a-zA-Z_-]+:.*?## / { printf "  \033[36m%-18s\033[0m %s\n", $$1, $$2 }' $(MAKEFILE_LIST)
	@printf "\n"

##@ 🎉 一键启动（前端 + 后端 + 基础设施）

start: ## 🚀 一键启动全栈（生产模式：infra + 后端 + worker + 前端构建/preview）
	@printf "$(PURPLE)$(DONE) 启动全栈 (start 模式)$(RESET)\n"
	docker compose up -d
	@printf "$(CYAN)⏳ 等待基础设施就绪$(RESET)\n"; sleep 3
	@printf "$(YELLOW)$(PKG) 构建前端$(RESET)\n"
	$(FRONTEND_BUILD)
	$(call ok,前端构建完成)
	@printf "$(PURPLE)$(BRAIN) 后端 + $(GEAR) Worker + $(ART) 前端 preview (Ctrl+C 停止)$(RESET)\n"
	@exec $(DEV_SERVICES) \
		--ready-url "http://localhost:$(BACKEND_PORT)/api/health" \
		--service "backend=$(BACKEND_RUN)" \
		--service "worker=$(WORKER_RUN)" \
		--service "beat=$(BEAT_RUN)" \
		--service "frontend=$(FRONTEND_RUN)"

hot: ## 🔥 一键启动全栈热重载（infra + 后端 reload + worker + 前端 HMR）
	@printf "$(PURPLE)$(FIRE) 启动全栈 (hot 模式)$(RESET)\n"
	docker compose up -d
	@printf "$(CYAN)⏳ 等待基础设施就绪$(RESET)\n"; sleep 3
	@printf "$(PURPLE)$(BRAIN) 后端热重载 + $(GEAR) Worker + $(BOLT) 前端 HMR (Ctrl+C 停止)$(RESET)\n"
	@exec $(DEV_SERVICES) \
		--ready-url "http://localhost:$(BACKEND_PORT)/api/health" \
		--service "backend=$(BACKEND_HOT)" \
		--service "worker=$(WORKER_RUN)" \
		--service "beat=$(BEAT_RUN)" \
		--service "frontend=$(FRONTEND_HOT)"

dev: hot ## 🔥 全栈热重载快捷入口（等价 make hot）

##@ 🧩 前后端分离启动（后端一套 / 前端一套）

backend-up: ## 🧠 启动后端整套（infra + 后端热重载 + Celery worker）
	@printf "$(PURPLE)$(BRAIN) 启动后端整套服务（含 watchdog Beat）$(RESET)\n"
	docker compose up -d
	@printf "$(CYAN)⏳ 等待基础设施就绪$(RESET)\n"; sleep 3
	@printf "$(PURPLE)$(FIRE) 后端热重载 + $(GEAR) Worker (Ctrl+C 停止)$(RESET)\n"
	@exec $(DEV_SERVICES) \
		--ready-url "http://localhost:$(BACKEND_PORT)/api/health" \
		--service "backend=$(BACKEND_HOT)" \
		--service "worker=$(WORKER_RUN)" \
		--service "beat=$(BEAT_RUN)"

frontend-up: ## 🎨 独立启动前端（Vite HMR，/api 代理到后端 8000）
	@printf "$(BLUE)$(ART) 独立启动前端 HMR -> http://localhost:$(FRONTEND_PORT)$(RESET)\n"
	@exec $(DEV_SERVICES) \
		--ready-url "http://localhost:$(FRONTEND_PORT)/" \
		--service "frontend=$(FRONTEND_HOT)"

##@ ⚙️ 组件独立启动（基础设施 / 后端 / 前端 / Worker）

infra: ## 🐳 启动基础设施（Postgres + Redis + MinIO）
	docker compose up -d
	$(call ok,基础设施已启动 (Postgres/Redis/MinIO))

infra-down: ## 🐳 停止基础设施
	docker compose down
	$(call ok,基础设施已停止)

db-migrate: ## 💾 运行数据库迁移（Alembic upgrade head）
	PYTHONPATH=. uv run --project backend alembic -c alembic.ini upgrade head
	$(call ok,数据库迁移完成)

start-backend: ## 🧠 启动 FastAPI 后端（无热重载）
	@printf "$(PURPLE)$(BRAIN) 启动 FastAPI 后端 -> http://localhost:$(BACKEND_PORT)$(RESET)\n"
	@exec $(DEV_SERVICES) \
		--ready-url "http://localhost:$(BACKEND_PORT)/api/health" \
		--service "backend=$(BACKEND_RUN)"

hot-backend: ## 🔥 启动 FastAPI 后端热重载
	@printf "$(PURPLE)$(FIRE) 启动 FastAPI 后端热重载 -> http://localhost:$(BACKEND_PORT)$(RESET)\n"
	@exec $(DEV_SERVICES) \
		--ready-url "http://localhost:$(BACKEND_PORT)/api/health" \
		--service "backend=$(BACKEND_HOT)"

start-worker: ## ⚙️ 启动 Celery worker（异步任务：简历解析等）
	@printf "$(YELLOW)$(GEAR) 启动 Celery worker$(RESET)\n"
	@exec $(DEV_SERVICES) --service "worker=$(WORKER_RUN)"

start-beat: ## ⏱️ 启动 Celery Beat（每 30 秒收敛超时简历任务）
	@printf "$(YELLOW)$(GEAR) 启动 Celery Beat watchdog$(RESET)\n"
	@exec $(DEV_SERVICES) --service "beat=$(BEAT_RUN)"

backend: hot-backend ## 🔥 后端热重载快捷入口

backend-worker: start-worker ## ⚙️ Worker 快捷入口

beat: start-beat ## ⏱️ Beat watchdog 快捷入口

start-frontend: ## 🎨 构建并启动前端 preview（无热重载）
	@printf "$(BLUE)$(ART) 构建并启动前端 preview -> http://localhost:$(FRONTEND_PORT)$(RESET)\n"
	$(FRONTEND_BUILD)
	$(call ok,前端构建完成)
	@exec $(DEV_SERVICES) \
		--ready-url "http://localhost:$(FRONTEND_PORT)/" \
		--service "frontend=$(FRONTEND_RUN)"

hot-frontend: ## ⚡ 启动 Vite 前端热重载（HMR）
	@printf "$(BLUE)$(BOLT) 启动 Vite 前端 HMR -> http://localhost:$(FRONTEND_PORT)$(RESET)\n"
	@exec $(DEV_SERVICES) \
		--ready-url "http://localhost:$(FRONTEND_PORT)/" \
		--service "frontend=$(FRONTEND_HOT)"

frontend: hot-frontend ## ⚡ 前端热重载快捷入口

##@ 🛠 初始化与开发工具

setup: ## 🚀 一键初始化项目（新机器首次运行）
	bash scripts/setup.sh
	$(call ok,项目初始化完成)

install: ## 📦 安装前后端依赖（uv sync + pnpm install）
	cd backend && uv sync
	cd frontend && pnpm install
	$(call ok,前后端依赖安装完成)

##@ 🧪 质量门禁（scripts/quality — 只读，不 --fix）

lint: ## 🧹 lint：ruff check + ruff format --check + pnpm lint
	@bash scripts/quality/lint.sh
	$(call ok,Lint 检查通过)

type-check: ## 🔎 类型检查：mypy backend + frontend tsc
	@bash scripts/quality/typecheck.sh
	$(call ok,类型检查通过)

arch-check: ## 🏗  架构分层检查（轻量；完整规则见 AIP-011）
	@PYTHONPATH=. uv run --project backend python scripts/quality/arch_check.py
	$(call ok,架构检查通过)

test-unit: ## 🧪 单元测试（backend unit；frontend 有 harness 时一并跑）
	@bash scripts/quality/test_unit.sh
	$(call ok,单元测试通过)

test-integration: ## 🔗 集成测试（需 Postgres:5433 + Redis:6379；缺失则 BLOCKED）
	@bash scripts/quality/test_integration.sh
	$(call ok,集成测试通过)

test-frontend: ## 🎨 前端测试（vitest run；无 harness 时 BLOCKED）
	@bash scripts/quality/test_frontend.sh
	$(call ok,前端测试通过)

test: ## 🧪 后端完整测试（unit + integration；integration 缺依赖则 BLOCKED）
	@bash scripts/quality/test_unit.sh
	@bash scripts/quality/test_integration.sh
	$(call ok,后端测试通过)

build: ## 📦 前端生产构建（tsc -b && vite build）
	@bash scripts/quality/build.sh
	$(call ok,构建通过)

ci-fast: ## ⚡ 快速 CI：lint + type + arch + unit + build（不含 integration）
	@bash scripts/quality/ci_fast.sh
	$(call ok,ci-fast 通过)

ci: ## 🎯 完整本地 CI：ci-fast + integration + frontend tests
	@bash scripts/quality/ci.sh
	$(call ok,ci 通过)

stop: ## 🛑 停止所有服务（infra + 后端 + worker + 前端）
	docker compose down
	@-pkill -f "uvicorn backend.main:app" 2>/dev/null || true
	@-pkill -f "celery.*backend" 2>/dev/null || true
	@-pkill -f "vite" 2>/dev/null || true
	$(call ok,所有服务已停止)

dev-stop: stop ## 🛑 停止服务快捷入口

clean: ## 🗑  清理构建产物（frontend/dist + __pycache__）
	rm -rf frontend/dist
	find backend -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
	$(call ok,构建产物已清理)
