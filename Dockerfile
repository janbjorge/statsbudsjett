FROM python:3.14-slim
COPY --from=ghcr.io/astral-sh/uv:latest /uv /bin/uv
WORKDIR /app
ENV UV_COMPILE_BYTECODE=1 UV_LINK_MODE=copy PATH="/app/.venv/bin:$PATH"
COPY pyproject.toml uv.lock ./
# Runtime dependencies only: the pipeline (polars, pypdf) and dev tools stay out of the image
RUN uv sync --locked --no-default-groups --no-install-project
COPY core core
COPY app app
COPY adapters adapters
COPY datasets datasets
USER nobody
EXPOSE 8080
CMD ["uvicorn", "adapters.web.main:app", "--host", "0.0.0.0", "--port", "8080", "--proxy-headers", "--forwarded-allow-ips", "*"]
