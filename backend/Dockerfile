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
