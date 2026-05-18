# Plan 0 — Architecture Standards & Project Scaffold

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Establish the full project skeleton, conventions, tooling, and CI/CD pipeline so every subsequent plan has a consistent foundation to build on.

**Architecture:** Monorepo with `backend/` (FastAPI) and `frontend/` (React/Vite) directories. Service/Repository pattern enforced from day one. All tooling configured before any feature code is written.

**Tech Stack:** Python 3.12, FastAPI, pytest, ruff, black, Node 20, React 18, Vite, TypeScript, ESLint, Vitest, GitHub Actions, commitlint, pre-commit

---

## File Map

```
saas-tracker/
  backend/
    src/
      domain/
        entities/         純資料結構 (dataclasses / Pydantic models)
        repositories/     Repository 介面 (ABC)
      application/
        services/         Business logic (use cases 改名 services)
        interfaces/       Email sender 等外部介面 (ABC)
      infrastructure/
        database/
          models.py       SQLAlchemy ORM models
          session.py      async engine + session factory
          repositories/   Sql*Repository 實作
        smtp/             SMTP sender 實作
        auth/             password hashing utils
      api/
        v1/
          routers/        FastAPI routers (一個功能一個 router)
          schemas/        Pydantic request/response schemas
          dependencies.py DI wiring
        middleware/       CSRF, logging, request ID
        exceptions.py     全域 exception handlers
        main.py           FastAPI app factory
    tests/
      unit/               Mock repository，不需 DB
      integration/        需要真實 DB (pytest-asyncio + test DB)
    alembic/
      versions/
      env.py
    alembic.ini
    pyproject.toml
    Dockerfile
    .env.example

  frontend/
    src/
      components/         通用 shadcn/ui 元件
      features/           功能模組
      pages/              頁面元件
      layouts/            AppLayout, AuthLayout
      hooks/              通用 custom hooks
      services/           axios instance, interceptors
      lib/                工具函式, zod schemas
      types/              全域 TypeScript types
    public/
    index.html
    vite.config.ts
    tailwind.config.ts
    tsconfig.json
    package.json
    Dockerfile

  docker-compose.yml
  docker-compose.dev.yml
  docker-compose.prod.yml
  .env.example
  .github/
    workflows/
      ci.yml
  .pre-commit-config.yaml
  commitlint.config.js
```

---

## Task 1: Backend Directory Skeleton

**Files:**
- Create: `backend/pyproject.toml`
- Create: `backend/src/domain/__init__.py` (and subdirs)
- Create: `backend/src/application/__init__.py` (and subdirs)
- Create: `backend/src/infrastructure/__init__.py` (and subdirs)
- Create: `backend/src/api/__init__.py` (and subdirs)
- Create: `backend/tests/__init__.py`
- Create: `backend/.env.example`

- [ ] **Step 1: Create backend directory structure**

```bash
cd backend
mkdir -p src/domain/entities src/domain/repositories
mkdir -p src/application/services src/application/interfaces
mkdir -p src/infrastructure/database/repositories src/infrastructure/smtp src/infrastructure/auth
mkdir -p src/api/v1/routers src/api/v1/schemas src/api/middleware
mkdir -p tests/unit tests/integration
touch src/domain/__init__.py src/domain/entities/__init__.py src/domain/repositories/__init__.py
touch src/application/__init__.py src/application/services/__init__.py src/application/interfaces/__init__.py
touch src/infrastructure/__init__.py src/infrastructure/database/__init__.py
touch src/infrastructure/database/repositories/__init__.py
touch src/infrastructure/smtp/__init__.py src/infrastructure/auth/__init__.py
touch src/api/__init__.py src/api/v1/__init__.py src/api/v1/routers/__init__.py
touch src/api/v1/schemas/__init__.py src/api/middleware/__init__.py
touch tests/__init__.py tests/unit/__init__.py tests/integration/__init__.py
```

- [ ] **Step 2: Create `backend/pyproject.toml`**

```toml
[build-system]
requires = ["setuptools>=68"]
build-backend = "setuptools.backends.legacy:build"

[project]
name = "subtrack-backend"
version = "0.1.0"
requires-python = ">=3.12"
dependencies = [
    "fastapi>=0.111.0",
    "uvicorn[standard]>=0.29.0",
    "gunicorn>=22.0.0",
    "sqlalchemy[asyncio]>=2.0.30",
    "asyncpg>=0.29.0",
    "alembic>=1.13.0",
    "pydantic>=2.7.0",
    "pydantic-settings>=2.2.0",
    "passlib[bcrypt]>=1.7.4",
    "python-jose[cryptography]>=3.3.0",
    "redis>=5.0.4",
    "slowapi>=0.1.9",
    "python-multipart>=0.0.9",
    "httpx>=0.27.0",
]

[project.optional-dependencies]
dev = [
    "pytest>=8.2.0",
    "pytest-asyncio>=0.23.0",
    "pytest-cov>=5.0.0",
    "ruff>=0.4.0",
    "black>=24.4.0",
]

[tool.setuptools.packages.find]
where = ["src"]

[tool.pytest.ini_options]
asyncio_mode = "auto"
testpaths = ["tests"]
pythonpath = ["src"]

[tool.ruff]
line-length = 100
target-version = "py312"

[tool.ruff.lint]
select = ["E", "F", "I", "UP"]

[tool.black]
line-length = 100
target-version = ["py312"]
```

- [ ] **Step 3: Create `backend/.env.example`**

```bash
# Database
DATABASE_URL=postgresql+asyncpg://subtrack:password@db:5432/subtrack

# Redis
REDIS_URL=redis://redis:6379/0

# JWT
JWT_ACCESS_SECRET_KEY=change-me-access
JWT_REFRESH_SECRET_KEY=change-me-refresh
JWT_ACCESS_EXPIRE_MINUTES=30
JWT_REFRESH_EXPIRE_DAYS=7

# CORS
CORS_ORIGINS=http://localhost:5173

# SMTP
SMTP_HOST=smtp.example.com
SMTP_PORT=587
SMTP_USER=noreply@example.com
SMTP_PASSWORD=change-me
SMTP_FROM=SubTrack <noreply@example.com>

# App
APP_ENV=development
SECRET_KEY=change-me-session
```

- [ ] **Step 4: Commit**

```bash
git add backend/
git commit -m "chore: scaffold backend directory structure and pyproject.toml"
```

---

## Task 2: Backend Base Classes (Service/Repository Pattern)

**Files:**
- Create: `backend/src/domain/repositories/base.py`
- Create: `backend/src/application/services/base.py`
- Create: `backend/src/api/v1/schemas/base.py`

- [ ] **Step 1: Write failing test for base response schema**

```python
# tests/unit/test_base_schemas.py
from api.v1.schemas.base import ApiResponse

def test_success_response():
    r = ApiResponse(success=True, data={"id": 1}, message="ok")
    assert r.success is True
    assert r.data == {"id": 1}
    assert r.meta is None

def test_error_response():
    r = ApiResponse(success=False, data=None, message="error")
    assert r.success is False
```

- [ ] **Step 2: Run test to verify it fails**

```bash
cd backend && pytest tests/unit/test_base_schemas.py -v
```

Expected: `ModuleNotFoundError` or `ImportError`

- [ ] **Step 3: Create `backend/src/api/v1/schemas/base.py`**

```python
from typing import Any, Generic, TypeVar
from pydantic import BaseModel

T = TypeVar("T")


class ApiResponse(BaseModel, Generic[T]):
    success: bool
    data: T | None = None
    message: str = ""
    meta: dict[str, Any] | None = None

    @classmethod
    def ok(cls, data: T = None, message: str = "", meta: dict | None = None) -> "ApiResponse[T]":
        return cls(success=True, data=data, message=message, meta=meta)

    @classmethod
    def fail(cls, message: str, data: T = None) -> "ApiResponse[T]":
        return cls(success=False, data=data, message=message)


class PaginationMeta(BaseModel):
    total: int
    limit: int
    offset: int
```

- [ ] **Step 4: Create `backend/src/domain/repositories/base.py`**

```python
from abc import ABC, abstractmethod
from typing import Generic, TypeVar

T = TypeVar("T")
ID = TypeVar("ID")


class BaseRepository(ABC, Generic[T, ID]):
    @abstractmethod
    async def get_by_id(self, id: ID) -> T | None: ...

    @abstractmethod
    async def list_all(self) -> list[T]: ...

    @abstractmethod
    async def save(self, entity: T) -> T: ...

    @abstractmethod
    async def delete(self, id: ID) -> None: ...
```

- [ ] **Step 5: Create `backend/src/application/services/base.py`**

```python
# Marker base — services inherit this to signal they are application-layer services.
# Do not add business logic here.
class BaseService:
    pass
```

- [ ] **Step 6: Run test to verify it passes**

```bash
cd backend && pytest tests/unit/test_base_schemas.py -v
```

Expected: PASS

- [ ] **Step 7: Commit**

```bash
git add backend/src/ backend/tests/
git commit -m "feat: add base repository, service, and API response schema"
```

---

## Task 3: Backend App Factory & Config

**Files:**
- Create: `backend/src/api/main.py`
- Create: `backend/src/api/config.py`

- [ ] **Step 1: Create `backend/src/api/config.py`**

```python
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    database_url: str
    redis_url: str

    jwt_access_secret_key: str
    jwt_refresh_secret_key: str
    jwt_access_expire_minutes: int = 30
    jwt_refresh_expire_days: int = 7

    cors_origins: list[str] = []

    smtp_host: str = ""
    smtp_port: int = 587
    smtp_user: str = ""
    smtp_password: str = ""
    smtp_from: str = ""

    app_env: str = "development"


settings = Settings()
```

- [ ] **Step 2: Create `backend/src/api/main.py`**

```python
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from api.config import settings


def create_app() -> FastAPI:
    app = FastAPI(
        title="SubTrack API",
        version="1.0.0",
        docs_url="/api/docs" if settings.app_env != "production" else None,
        redoc_url=None,
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=True,
        allow_methods=["GET", "POST", "PUT", "DELETE", "PATCH"],
        allow_headers=["*", "X-CSRF-Token"],
    )

    @app.get("/health")
    async def health() -> dict:
        return {"status": "ok"}

    return app


app = create_app()
```

- [ ] **Step 3: Write test for health endpoint**

```python
# tests/unit/test_health.py
from fastapi.testclient import TestClient
from api.main import app

client = TestClient(app)

def test_health():
    r = client.get("/health")
    assert r.status_code == 200
    assert r.json() == {"status": "ok"}
```

- [ ] **Step 4: Run test**

```bash
cd backend && pytest tests/unit/test_health.py -v
```

Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add backend/src/api/
git commit -m "feat: add FastAPI app factory, config, and /health endpoint"
```

---

## Task 4: Frontend Directory Skeleton

**Files:**
- Create: `frontend/` (Vite + React + TypeScript project)

- [ ] **Step 1: Scaffold Vite project**

```bash
cd frontend  # (from repo root: mkdir frontend && cd frontend)
npm create vite@latest . -- --template react-ts
npm install
```

- [ ] **Step 2: Install core dependencies**

```bash
npm install \
  react-router-dom@6 \
  @tanstack/react-query \
  zustand \
  axios \
  react-hook-form \
  @hookform/resolvers \
  zod \
  lucide-react

npm install -D \
  tailwindcss \
  postcss \
  autoprefixer \
  @types/node \
  vitest \
  @vitest/ui \
  @testing-library/react \
  @testing-library/jest-dom \
  @testing-library/user-event \
  jsdom \
  eslint \
  @typescript-eslint/eslint-plugin \
  @typescript-eslint/parser
```

- [ ] **Step 3: Initialise Tailwind**

```bash
npx tailwindcss init -p
```

Update `tailwind.config.ts`:

```ts
import type { Config } from "tailwindcss";

export default {
  content: ["./index.html", "./src/**/*.{ts,tsx}"],
  theme: { extend: {} },
  plugins: [],
} satisfies Config;
```

Update `src/index.css`:

```css
@tailwind base;
@tailwind components;
@tailwind utilities;
```

- [ ] **Step 4: Create frontend directory structure**

```bash
mkdir -p src/components src/features src/pages src/layouts src/hooks src/services src/lib src/types
touch src/components/.gitkeep src/features/.gitkeep
```

- [ ] **Step 5: Configure Vitest in `vite.config.ts`**

```ts
import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";
import path from "path";

export default defineConfig({
  plugins: [react()],
  resolve: {
    alias: { "@": path.resolve(__dirname, "./src") },
  },
  test: {
    globals: true,
    environment: "jsdom",
    setupFiles: ["./src/test-setup.ts"],
  },
});
```

Create `src/test-setup.ts`:

```ts
import "@testing-library/jest-dom";
```

- [ ] **Step 6: Write a smoke test**

```ts
// src/lib/utils.test.ts
import { describe, it, expect } from "vitest";

function cn(...classes: string[]) {
  return classes.filter(Boolean).join(" ");
}

describe("cn utility", () => {
  it("joins class names", () => {
    expect(cn("a", "b")).toBe("a b");
    expect(cn("a", "", "b")).toBe("a b");
  });
});
```

Create `src/lib/utils.ts`:

```ts
export function cn(...classes: (string | undefined | null | false)[]) {
  return classes.filter(Boolean).join(" ");
}
```

- [ ] **Step 7: Run test**

```bash
cd frontend && npx vitest run
```

Expected: PASS

- [ ] **Step 8: Commit**

```bash
git add frontend/
git commit -m "chore: scaffold frontend with Vite, React, Tailwind, Vitest"
```

---

## Task 5: shadcn/ui Initialisation

**Files:**
- Modify: `frontend/components.json`
- Create: `frontend/src/components/ui/` (shadcn components)

- [ ] **Step 1: Initialise shadcn/ui**

```bash
cd frontend
npx shadcn@latest init
```

When prompted:
- Style: **Default**
- Base color: **Neutral**
- CSS variables: **Yes**

- [ ] **Step 2: Add core components used throughout the app**

```bash
npx shadcn@latest add button badge input select table card dialog alert toast
```

- [ ] **Step 3: Verify components exist**

```bash
ls src/components/ui/
```

Expected: `button.tsx`, `badge.tsx`, `input.tsx`, `select.tsx`, `table.tsx`, `card.tsx`, `dialog.tsx`, `alert.tsx`, `toast.tsx`

- [ ] **Step 4: Commit**

```bash
git add frontend/src/components/ui/ frontend/components.json frontend/src/
git commit -m "chore: add shadcn/ui with core components"
```

---

## Task 6: Pre-commit Hooks & Commit Convention

**Files:**
- Create: `.pre-commit-config.yaml`
- Create: `commitlint.config.js`
- Create: `package.json` (root, for commitlint)

- [ ] **Step 1: Install pre-commit (Python side)**

```bash
pip install pre-commit
```

- [ ] **Step 2: Create `.pre-commit-config.yaml` at repo root**

```yaml
repos:
  - repo: https://github.com/astral-sh/ruff-pre-commit
    rev: v0.4.4
    hooks:
      - id: ruff
        args: [--fix]
        files: ^backend/
      - id: ruff-format
        files: ^backend/

  - repo: https://github.com/pre-commit/mirrors-eslint
    rev: v8.57.0
    hooks:
      - id: eslint
        files: ^frontend/src/.*\.[jt]sx?$
        additional_dependencies:
          - eslint@8
          - "@typescript-eslint/parser@7"
          - "@typescript-eslint/eslint-plugin@7"

  - repo: https://github.com/alessandrojcm/commitlint-pre-commit-hook
    rev: v9.13.0
    hooks:
      - id: commitlint
        stages: [commit-msg]
        additional_dependencies: ["@commitlint/config-conventional"]
```

- [ ] **Step 3: Create `commitlint.config.js` at repo root**

```js
module.exports = {
  extends: ["@commitlint/config-conventional"],
  rules: {
    "type-enum": [
      2,
      "always",
      ["feat", "fix", "refactor", "chore", "test", "docs"],
    ],
  },
};
```

- [ ] **Step 4: Install pre-commit hooks**

```bash
pre-commit install
pre-commit install --hook-type commit-msg
```

- [ ] **Step 5: Run pre-commit against all files to verify**

```bash
pre-commit run --all-files
```

Expected: ruff and eslint run, no blocking errors (warnings ok).

- [ ] **Step 6: Commit**

```bash
git add .pre-commit-config.yaml commitlint.config.js
git commit -m "chore: add pre-commit hooks for ruff, eslint, and commitlint"
```

---

## Task 7: CI/CD Pipeline (GitHub Actions)

**Files:**
- Create: `.github/workflows/ci.yml`

- [ ] **Step 1: Create `.github/workflows/ci.yml`**

```yaml
name: CI

on:
  push:
    branches: [main, develop]
  pull_request:
    branches: [main]

jobs:
  backend:
    runs-on: ubuntu-latest
    defaults:
      run:
        working-directory: backend

    services:
      postgres:
        image: postgres:15
        env:
          POSTGRES_USER: subtrack
          POSTGRES_PASSWORD: testpass
          POSTGRES_DB: subtrack_test
        ports: ["5432:5432"]
        options: >-
          --health-cmd pg_isready
          --health-interval 10s
          --health-timeout 5s
          --health-retries 5
      redis:
        image: redis:7
        ports: ["6379:6379"]

    steps:
      - uses: actions/checkout@v4

      - uses: actions/setup-python@v5
        with:
          python-version: "3.12"
          cache: pip

      - name: Install dependencies
        run: pip install -e ".[dev]"

      - name: Lint (ruff)
        run: ruff check src/ tests/

      - name: Format check (ruff)
        run: ruff format --check src/ tests/

      - name: Run unit tests
        run: pytest tests/unit/ -v --cov=src --cov-report=term-missing

      - name: Run integration tests
        env:
          DATABASE_URL: postgresql+asyncpg://subtrack:testpass@localhost:5432/subtrack_test
          REDIS_URL: redis://localhost:6379/0
          JWT_ACCESS_SECRET_KEY: test-access-secret
          JWT_REFRESH_SECRET_KEY: test-refresh-secret
          CORS_ORIGINS: '["http://localhost:5173"]'
        run: pytest tests/integration/ -v

  frontend:
    runs-on: ubuntu-latest
    defaults:
      run:
        working-directory: frontend

    steps:
      - uses: actions/checkout@v4

      - uses: actions/setup-node@v4
        with:
          node-version: "20"
          cache: npm
          cache-dependency-path: frontend/package-lock.json

      - name: Install dependencies
        run: npm ci

      - name: Lint
        run: npx eslint src/

      - name: Type check
        run: npx tsc --noEmit

      - name: Run tests
        run: npx vitest run

      - name: Build
        run: npm run build
```

- [ ] **Step 2: Verify the workflow file is valid YAML**

```bash
python -c "import yaml; yaml.safe_load(open('.github/workflows/ci.yml'))"
```

Expected: No output (valid YAML)

- [ ] **Step 3: Commit**

```bash
git add .github/
git commit -m "chore: add GitHub Actions CI pipeline"
```

---

## Task 8: Root Docker Compose Base

**Files:**
- Create: `docker-compose.yml`
- Create: `docker-compose.dev.yml`
- Create: `docker-compose.prod.yml`
- Create: `.env.example` (root)

- [ ] **Step 1: Create `docker-compose.yml` (base — shared definitions)**

```yaml
version: "3.9"

networks:
  subtrack:
    driver: bridge

volumes:
  postgres_data:
  redis_data:

services:
  db:
    image: postgres:15-alpine
    environment:
      POSTGRES_USER: ${POSTGRES_USER}
      POSTGRES_PASSWORD: ${POSTGRES_PASSWORD}
      POSTGRES_DB: ${POSTGRES_DB}
    volumes:
      - postgres_data:/var/lib/postgresql/data
    networks:
      - subtrack
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U ${POSTGRES_USER}"]
      interval: 10s
      timeout: 5s
      retries: 5

  redis:
    image: redis:7-alpine
    volumes:
      - redis_data:/data
    networks:
      - subtrack
    healthcheck:
      test: ["CMD", "redis-cli", "ping"]
      interval: 10s
      timeout: 5s
      retries: 5

  api:
    build:
      context: ./backend
    env_file: .env
    depends_on:
      db:
        condition: service_healthy
      redis:
        condition: service_healthy
    networks:
      - subtrack
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8000/health"]
      interval: 15s
      timeout: 5s
      retries: 5
```

- [ ] **Step 2: Create `docker-compose.dev.yml`**

```yaml
version: "3.9"

services:
  db:
    ports:
      - "5432:5432"

  redis:
    ports:
      - "6379:6379"

  api:
    build:
      target: development
    command: uvicorn api.main:app --host 0.0.0.0 --port 8000 --reload
    ports:
      - "8000:8000"
    volumes:
      - ./backend/src:/app/src

  web:
    build:
      context: ./frontend
      target: development
    ports:
      - "5173:5173"
    volumes:
      - ./frontend/src:/app/src
    environment:
      - VITE_API_URL=http://localhost:8000
```

- [ ] **Step 3: Create `docker-compose.prod.yml`**

```yaml
version: "3.9"

services:
  api:
    build:
      target: production
    command: gunicorn api.main:app -w 4 -k uvicorn.workers.UvicornWorker --bind 0.0.0.0:8000
    restart: unless-stopped

  scheduler:
    build:
      context: ./backend
      target: production
    command: python -m infrastructure.scheduler.main
    env_file: .env
    depends_on:
      db:
        condition: service_healthy
      redis:
        condition: service_healthy
    networks:
      - subtrack
    restart: unless-stopped

  web:
    build:
      context: ./frontend
      target: production
    ports:
      - "80:80"
    depends_on:
      api:
        condition: service_healthy
    networks:
      - subtrack
    restart: unless-stopped
```

- [ ] **Step 4: Create root `.env.example`**

```bash
# PostgreSQL
POSTGRES_USER=subtrack
POSTGRES_PASSWORD=change-me
POSTGRES_DB=subtrack

# (same as backend .env)
DATABASE_URL=postgresql+asyncpg://subtrack:change-me@db:5432/subtrack
REDIS_URL=redis://redis:6379/0
JWT_ACCESS_SECRET_KEY=change-me-access
JWT_REFRESH_SECRET_KEY=change-me-refresh
CORS_ORIGINS=http://localhost:5173
SMTP_HOST=
SMTP_PORT=587
SMTP_USER=
SMTP_PASSWORD=
SMTP_FROM=
APP_ENV=production
SECRET_KEY=change-me
```

- [ ] **Step 5: Commit**

```bash
git add docker-compose.yml docker-compose.dev.yml docker-compose.prod.yml .env.example
git commit -m "chore: add Docker Compose base, dev, and prod configurations"
```

---

## Task 9: Backend Dockerfile

**Files:**
- Create: `backend/Dockerfile`

- [ ] **Step 1: Create `backend/Dockerfile`**

```dockerfile
FROM python:3.12-slim AS base
WORKDIR /app
RUN addgroup --system app && adduser --system --group app

FROM base AS development
COPY pyproject.toml .
RUN pip install --no-cache-dir -e ".[dev]"
COPY src/ ./src/
USER app
EXPOSE 8000

FROM base AS production
COPY pyproject.toml .
RUN pip install --no-cache-dir -e "."
COPY src/ ./src/
USER app
EXPOSE 8000
```

- [ ] **Step 2: Verify Docker build (development target)**

```bash
cd backend && docker build --target development -t subtrack-api:dev .
```

Expected: Build completes without error.

- [ ] **Step 3: Commit**

```bash
git add backend/Dockerfile
git commit -m "chore: add backend multi-stage Dockerfile (dev + production)"
```

---

## Task 10: Frontend Dockerfile

**Files:**
- Create: `frontend/Dockerfile`
- Create: `frontend/nginx.conf`

- [ ] **Step 1: Create `frontend/nginx.conf`**

```nginx
server {
    listen 80;
    server_name _;
    root /usr/share/nginx/html;
    index index.html;

    gzip on;
    gzip_types text/plain text/css application/json application/javascript text/xml application/xml text/javascript;

    add_header X-Frame-Options "DENY";
    add_header X-Content-Type-Options "nosniff";
    add_header Referrer-Policy "strict-origin-when-cross-origin";
    add_header Permissions-Policy "camera=(), microphone=(), geolocation=()";

    location / {
        try_files $uri /index.html;
    }

    location /api/ {
        proxy_pass http://api:8000/api/;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_read_timeout 120s;
    }
}
```

- [ ] **Step 2: Create `frontend/Dockerfile`**

```dockerfile
FROM node:20-alpine AS development
WORKDIR /app
COPY package*.json .
RUN npm ci
COPY . .
EXPOSE 5173
CMD ["npm", "run", "dev", "--", "--host"]

FROM node:20-alpine AS builder
WORKDIR /app
COPY package*.json .
RUN npm ci
COPY . .
RUN npm run build

FROM nginx:alpine AS production
COPY --from=builder /app/dist /usr/share/nginx/html
COPY nginx.conf /etc/nginx/conf.d/default.conf
EXPOSE 80
```

- [ ] **Step 3: Verify Docker build (production target)**

```bash
cd frontend && docker build --target production -t subtrack-web:prod .
```

Expected: Build completes without error.

- [ ] **Step 4: Commit**

```bash
git add frontend/Dockerfile frontend/nginx.conf
git commit -m "chore: add frontend multi-stage Dockerfile and Nginx config"
```

---

## Plan 0 Complete

At this point you have:
- Full monorepo structure for backend and frontend
- Service/Repository base classes
- FastAPI app factory with `/health` endpoint
- Vite + React + Tailwind + shadcn/ui bootstrapped
- Vitest + pytest configured with first passing tests
- Pre-commit hooks (ruff, eslint, commitlint)
- GitHub Actions CI pipeline
- Docker Compose (base / dev / prod)
- Dockerfiles for both services

Verify the whole stack by running:

```bash
# Backend unit tests
cd backend && pytest tests/unit/ -v

# Frontend tests
cd frontend && npx vitest run

# Docker dev stack (db + redis only for now)
docker compose -f docker-compose.yml -f docker-compose.dev.yml up db redis
```

Then move on to **Plan 1 — Backend Infrastructure**.
