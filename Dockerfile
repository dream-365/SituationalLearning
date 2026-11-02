# syntax=docker/dockerfile:1
FROM ghcr.io/astral-sh/uv:0.11.6 AS builder

WORKDIR /app
ENV UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy

COPY pyproject.toml uv.lock README.md ./
COPY src ./src
RUN uv sync --frozen --no-dev --no-install-project
RUN uv sync --frozen --no-dev

FROM python:3.12-slim AS runtime

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PATH="/app/.venv/bin:$PATH" \
    SITULEARN_DATA_DIR=/data \
    SITULEARN_BACKUP_DIR=/backup

RUN groupadd --gid 10001 situlearn \
    && useradd --uid 10001 --gid 10001 --create-home situlearn \
    && mkdir -p /app /data /backup /tmp \
    && chown -R 10001:10001 /app /data /backup

WORKDIR /app
COPY --from=builder /app/.venv /app/.venv
COPY --from=builder /app/src /app/src
COPY pyproject.toml README.md ./

USER 10001:10001
EXPOSE 8000

CMD ["uvicorn", "situlearn.web.app:app", "--host", "0.0.0.0", "--port", "8000", "--proxy-headers", "--forwarded-allow-ips=*"]
