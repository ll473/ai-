FROM node:22-alpine AS frontend-build

WORKDIR /app/frontend
COPY frontend/package.json frontend/pnpm-lock.yaml ./
RUN corepack enable && pnpm install --frozen-lockfile
COPY frontend/ ./
RUN pnpm build

FROM python:3.12-slim AS runtime

WORKDIR /app
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

COPY pyproject.toml uv.lock README.md alembic.ini ./
COPY backend/ ./backend/
RUN pip install --no-cache-dir uv && uv sync --frozen --no-dev --no-editable

ENV PATH="/app/.venv/bin:$PATH"

COPY main.py ./
COPY uploads/demo-products/ ./uploads/demo-products/
COPY --from=frontend-build /app/frontend/dist ./frontend/dist

EXPOSE 8000
CMD ["sh", "-c", "python -m backend.scripts.migrate && python -m backend.scripts.setup_ai && python -m backend.scripts.seed_demo && exec uvicorn backend.app.main:app --host 0.0.0.0 --port ${PORT:-8000}"]
