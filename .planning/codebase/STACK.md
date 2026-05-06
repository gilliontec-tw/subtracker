# Technology Stack

**Analysis Date:** 2026-05-06

## Languages

**Primary:**
- Python 3.11+ — entire application (backend, templates, scripts)

## Runtime

**Environment:**
- CPython 3.11+

**Package Manager:**
- pip
- Lockfile: `requirements.txt` (pinned versions present)

## Frameworks

**Core:**
- FastAPI 0.115.6 — HTTP framework, routing, dependency injection
- Uvicorn 0.32.1 (standard extras) — ASGI server, entry point via `main.py`
- Jinja2 3.1.4 — server-side HTML templating (`src/interfaces/web/templates/`)

**Testing:**
- pytest 8.3.4 — test runner (config in `pyproject.toml`, `pythonpath = ["src"]`)
- pytest-mock 3.14.0 — mock fixtures
- httpx 0.28.1 — async HTTP client (used in integration-style tests)

**Build/Dev:**
- python-dotenv 1.0.1 — `.env` loading in `main.py`, `session.py`, `smtp_email_sender.py`
- python-multipart 0.0.20 — form data parsing for FastAPI

## Key Dependencies

**Critical:**
- SQLAlchemy 2.0.36 — ORM and query layer; models in `src/infrastructure/database/models.py`
- pyodbc 5.2.0 — low-level ODBC driver adapter for SQL Server; required by SQLAlchemy's `mssql+pyodbc` dialect
- passlib[bcrypt] 1.7.4 — password hashing interface; bcrypt backend used in `src/infrastructure/auth/hash_utils.py`
- itsdangerous 2.2.0 — signed session cookie serialization in `src/interfaces/web/session.py` (7-day TTL, `URLSafeTimedSerializer`)

**Infrastructure:**
- Python stdlib `smtplib` + `email.mime` — SMTP email sending in `src/infrastructure/email/smtp_email_sender.py` (no third-party email library)
- Python stdlib `logging` — file + stdout logging in `scripts/run_notifications.py`

## Configuration

**Environment:**
- Loaded via `python-dotenv` (`load_dotenv()` in `main.py`, `session.py`, `smtp_email_sender.py`, `session.py`)
- Required vars: `DB_CONNECTION_STRING`, `SMTP_HOST`, `SMTP_PORT`, `SMTP_USERNAME`, `SMTP_PASSWORD`, `SMTP_FROM`
- Optional vars: `APP_HOST` (default `0.0.0.0`), `APP_PORT` (default `8000`), `SECRET_KEY` (insecure dev default present)

**Build:**
- `pyproject.toml` — project name (`subtrack`), Python version constraint (`>=3.11`), pytest path config
- `requirements.txt` — all pinned runtime + dev dependencies

## Platform Requirements

**Development:**
- Python 3.11+
- ODBC Driver 17 for SQL Server (system-level driver, not a pip package)
- SQL Server instance (tested with `localhost\SQLEXPRESS`)

**Production:**
- Windows (primary target; Task Scheduler used for notification cron job)
- Linux supported for notification cron (`crontab` example in `scripts/run_notifications.py`)
- No containerization or Docker configuration present
- Static files served by FastAPI's `StaticFiles` mount at `/static` → `src/interfaces/web/static/`

---

*Stack analysis: 2026-05-06*
