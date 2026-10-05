FROM node:22-slim AS frontend
WORKDIR /app/frontend
COPY frontend/package.json frontend/package-lock.json ./
RUN npm ci
COPY frontend ./
# Writes to /app/src/blattwerk/static.
RUN npm run build

FROM ghcr.io/astral-sh/uv:python3.14-bookworm-slim
WORKDIR /app
ENV UV_COMPILE_BYTECODE=1 UV_LINK_MODE=copy UV_NO_DEV=1
COPY pyproject.toml uv.lock README.md ./
RUN uv sync --locked --no-install-project
COPY src ./src
COPY --from=frontend /app/src/blattwerk/static ./src/blattwerk/static
RUN uv sync --locked
# Same uid as the host user, so the bind-mounted data dir stays writable.
USER 1000:1000
ENV BLATTWERK_DATA_DIR=/data
# Caddy is the only client, so its forwarded headers carry the real IP for the login limit.
CMD ["/app/.venv/bin/uvicorn", "blattwerk.app:app", "--host", "0.0.0.0", "--port", "8000", "--proxy-headers", "--forwarded-allow-ips", "*"]
