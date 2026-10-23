# Repository Guidelines

## Project Structure & Module Organization

Notebook is a personal AI knowledge base with a Next.js frontend, FastAPI backend, ARQ worker, and Electron macOS shell.

- `apps/api/app/`: API routers, Pydantic schemas, SQLAlchemy models, and service logic. Keep business logic in `services/`.
- `apps/web/src/`: App Router pages in `app/`, reusable UI in `components/`, and API helpers in `lib/`. Static assets live in `apps/web/public/`.
- `apps/worker/`: background job configuration; `apps/desktop/`: Electron launcher and icon tooling.
- `tests/api/`: Python tests; shared fixtures are in `tests/conftest.py`.
- `migrations/`: Alembic migrations; `infrastructure/`: PostgreSQL/pgvector and Redis Compose setup; `docs/`: architecture and development notes.

## Build, Test, and Development Commands

Use Python 3.12, Node.js 22, pnpm 10.12.1, `uv`, `fnm`, and Docker Desktop. Run commands from the repository root.

- `make setup`: create `.env` if missing and install Python/Node dependencies.
- `make infra-up && make migrate`: start database/cache services and apply migrations.
- `make api`, `make worker`, `make web`: run development processes in separate terminals.
- `make check`: run Ruff, pytest, ESLint, and TypeScript checks.
- `pnpm build:web`: build the production frontend with Node.js 22 active.
- `pnpm dev:desktop` / `pnpm build:desktop`: launch Electron or build the macOS app.
- `make migration message='describe change'`: generate a migration; review it before applying.

## Coding Style & Naming Conventions

Use four-space indentation, type annotations, and snake_case names in Python. Ruff targets Python 3.12 with a 100-character line limit and import-order checks. Match existing TypeScript style: two spaces, double quotes, semicolons, PascalCase components, and kebab-case filenames such as `knowledge-list-panel.tsx`. Use ESLint's Next.js and TypeScript rules; no separate formatter is configured.

## Testing Guidelines

Use pytest and pytest-asyncio with `test_*.py` files and descriptive `test_*` functions. Run `uv run pytest` or a focused file such as `uv run pytest tests/api/test_search.py`. Fixtures provide in-memory SQLite, an HTTPX API client, and a fake job queue. Validate PostgreSQL-specific behavior against local infrastructure. No coverage threshold or frontend test runner is configured; check UI changes manually alongside lint/type checks.

## Commit & Pull Request Guidelines

Follow existing Conventional Commit patterns: `feat(web): ...`, `fix(desktop): ...`, or `chore: ...`; recent descriptions use Chinese. Keep commits focused. PRs should explain behavior changes, list validation performed, link relevant issues, and include screenshots for UI changes. Highlight migrations and configuration changes.

## Security & Configuration

Keep credentials in ignored `.env` and runtime settings/uploads in ignored `data/`. Never commit secrets; document new configuration keys with safe placeholders in `.env.example`.
