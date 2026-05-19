FROM python:3.12-slim
WORKDIR /app
COPY pyproject.toml .
RUN pip install --no-cache-dir .
COPY env_service/ env_service/
CMD ["uvicorn", "env_service.main:app", "--host", "0.0.0.0", "--port", "8000"]
