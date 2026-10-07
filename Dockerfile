FROM python:3.14-slim
COPY --from=ghcr.io/astral-sh/uv:latest /uv /bin/uv
WORKDIR /app
ENV UV_COMPILE_BYTECODE=1 UV_LINK_MODE=copy PATH="/app/.venv/bin:$PATH" PYTHONPATH=/app/src
COPY pyproject.toml uv.lock ./
# Runtime dependencies only: the pipeline (polars, pypdf) and dev tools stay out of the image
RUN uv sync --locked --no-default-groups --no-install-project
COPY src src
# Commit for Logfire's service version and source links: fly deploy --build-arg GIT_SHA=$(git rev-parse HEAD)
ARG GIT_SHA=main
ENV GIT_SHA=$GIT_SHA
COPY datasets datasets
USER nobody
EXPOSE 8080
CMD ["uvicorn", "adapters.web.main:app", "--host", "0.0.0.0", "--port", "8080", "--proxy-headers", "--forwarded-allow-ips", "*"]
