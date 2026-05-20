FROM ghcr.io/astral-sh/uv:python3.12-bookworm-slim AS builder
WORKDIR /app
ENV UV_COMPILE_BYTECODE=1
ENV UV_LINK_MODE=copy
COPY pyproject.toml uv.lock ./
COPY common common/
COPY services/simulation services/simulation/
RUN uv sync --frozen --package sim-service --no-dev

FROM python:3.12-slim
WORKDIR /app
COPY --from=builder /app/.venv /app/.venv
COPY common common/
COPY services/simulation services/simulation/
ENV PATH="/app/.venv/bin:$PATH"
CMD ["uvicorn", "sim_service.main:app", "--host", "0.0.0.0", "--port", "8000"]
