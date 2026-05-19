FROM python:3.12-slim
WORKDIR /app
COPY pyproject.toml .
RUN pip install --no-cache-dir .
COPY gateway_service/ gateway_service/
CMD ["uvicorn", "gateway_service.main:app", "--host", "0.0.0.0", "--port", "8000"]
