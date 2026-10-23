SHELL := /bin/sh

NODE_VERSION := $(shell cat .nvmrc)
NODE_RUN := fnm exec --using=$(NODE_VERSION) --

.PHONY: setup node-version infra-up infra-down infra-logs migrate migration api worker web check

setup:
	@test -f .env || cp .env.example .env
	uv sync --all-groups
	@command -v fnm >/dev/null || (echo "fnm is required; install it with: brew install fnm" && exit 1)
	fnm install $(NODE_VERSION)
	$(NODE_RUN) pnpm install

node-version:
	@printf "system Node: "
	@node --version
	@printf "project Node: "
	@$(NODE_RUN) node --version

infra-up:
	docker compose --env-file .env -f infrastructure/compose.yml up -d --wait

infra-down:
	docker compose --env-file .env -f infrastructure/compose.yml down

infra-logs:
	docker compose --env-file .env -f infrastructure/compose.yml logs -f

migrate:
	uv run alembic upgrade head

migration:
	@test -n "$(message)" || (echo "usage: make migration message='describe change'" && exit 1)
	uv run alembic revision --autogenerate -m "$(message)"

api:
	uv run uvicorn apps.api.app.main:app --reload --host 127.0.0.1 --port 8000

worker:
	uv run arq apps.worker.worker.settings.WorkerSettings

web:
	$(NODE_RUN) pnpm --filter @notebook/web dev

check:
	uv run ruff check .
	uv run pytest
	$(NODE_RUN) pnpm --filter @notebook/web lint
	$(NODE_RUN) pnpm --filter @notebook/web typecheck
