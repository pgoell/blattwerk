FROM node:22-slim AS frontend
WORKDIR /app/frontend
COPY frontend/package.json frontend/package-lock.json ./
RUN npm ci
COPY frontend ./
# The Claude Desktop extension (frontend/mcpb.mjs) bundles the docs and reads the sheet schema.
COPY docs/okf /app/docs/okf
COPY src/blattwerk/sheet.schema.json /app/src/blattwerk/sheet.schema.json
# Writes to /app/src/blattwerk/static, the extension blattomat.mcpb included.
RUN npm run build

FROM ghcr.io/astral-sh/uv:python3.14-bookworm-slim
WORKDIR /app
# The base image still trusts emSign ECC Root CA - G3, which Mozilla dropped. The security repo's ca-certificates no longer does.
RUN apt-get update && apt-get install --only-upgrade -y ca-certificates && rm -rf /var/lib/apt/lists/*
ENV UV_COMPILE_BYTECODE=1 UV_LINK_MODE=copy UV_NO_DEV=1
COPY pyproject.toml uv.lock README.md ./
RUN uv sync --locked --no-install-project
# Chromium prints the PDF. It lies where the app's user can read it, with the system libraries it needs.
ENV PLAYWRIGHT_BROWSERS_PATH=/ms-playwright
RUN /app/.venv/bin/playwright install --with-deps --only-shell chromium && rm -rf /var/lib/apt/lists/*
COPY src ./src
COPY --from=frontend /app/src/blattwerk/static ./src/blattwerk/static
RUN uv sync --locked
# The deploy's smoke test. It runs in this container, so it comes with the image it tests.
COPY scripts/smoke.py ./scripts/smoke.py
# The remote MCP route runs its child with this node and this bundle.
COPY --from=frontend /usr/local/bin/node /usr/local/bin/node
COPY --from=frontend /app/frontend/.mcp-http/http.mjs /app/mcp/http.mjs
COPY docs/okf /app/docs/okf
# Same uid as the host user, so the bind-mounted data dir stays writable.
USER 1000:1000
ENV BLATTWERK_DATA_DIR=/data BLATTWERK_MCP_HTTP=/app/mcp/http.mjs BLATTWERK_DOCS=/app/docs/okf
# Caddy is the only client, so its forwarded headers carry the real IP for the login limit.
CMD ["/app/.venv/bin/uvicorn", "blattwerk.app:app", "--host", "0.0.0.0", "--port", "8000", "--proxy-headers", "--forwarded-allow-ips", "*"]
