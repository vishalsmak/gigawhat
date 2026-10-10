# syntax=docker/dockerfile:1
# The hosted image: cloud profile only, so no PyTorch, Docling or local models.

FROM python:3.12-slim-bookworm AS build
ENV UV_COMPILE_BYTECODE=1 UV_LINK_MODE=copy UV_PYTHON_DOWNLOADS=never
RUN pip install --no-cache-dir uv==0.11.28
WORKDIR /app
COPY pyproject.toml uv.lock ./
RUN --mount=type=cache,target=/root/.cache/uv uv sync --frozen --no-dev --no-install-project
COPY README.md LICENSE ./
COPY src ./src
RUN --mount=type=cache,target=/root/.cache/uv uv sync --frozen --no-dev

FROM python:3.12-slim-bookworm
RUN useradd --create-home --uid 10001 gigawhat
WORKDIR /app
# Chainlit writes uploads and translations next to its config, so the app directory is the app's.
RUN chown gigawhat:gigawhat /app
COPY --from=build --chown=gigawhat:gigawhat /app /app
COPY --chown=gigawhat:gigawhat .chainlit/config.toml ./.chainlit/config.toml
COPY --chown=gigawhat:gigawhat chainlit.md ./
ENV PATH="/app/.venv/bin:$PATH" PYTHONUNBUFFERED=1 GIGAWHAT_PROFILE=cloud \
    NEMO_GUARDRAILS_NO_USAGE_STATS=1 HF_HUB_DISABLE_TELEMETRY=1
USER gigawhat
EXPOSE 8000
HEALTHCHECK --interval=30s --timeout=5s --start-period=60s \
  CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8000/health')"
CMD ["uvicorn", "gigawhat.api:app", "--host", "0.0.0.0", "--port", "8000", \
     "--proxy-headers", "--forwarded-allow-ips", "*"]
