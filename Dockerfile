FROM python:3.11-slim AS builder

WORKDIR /build
RUN pip install --no-cache-dir uv

COPY pyproject.toml uv.lock ./
RUN uv pip install --system --no-compile -r pyproject.toml 2>/dev/null || \
    pip install --no-cache-dir -e .

FROM python:3.11-slim AS runtime

WORKDIR /app
COPY --from=builder /usr/local/lib/python3.11/site-packages /usr/local/lib/python3.11/site-packages
COPY . .

EXPOSE 8000
ENV PYTHONUNBUFFERED=1

ENTRYPOINT ["python", "-m", "src"]
CMD ["--host", "0.0.0.0", "--port", "8000"]
