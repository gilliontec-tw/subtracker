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
RUN apt-get update && apt-get install -y --no-install-recommends curl && rm -rf /var/lib/apt/lists/*
COPY pyproject.toml .
COPY src/ ./src/
RUN pip install --no-cache-dir -e "."
COPY alembic/ ./alembic/
COPY alembic.ini .
COPY scripts/ ./scripts/
COPY entrypoint.sh .
RUN chmod +x entrypoint.sh
USER app
EXPOSE 8000
ENTRYPOINT ["./entrypoint.sh"]
