FROM python:3.12-slim
WORKDIR /app
COPY pyproject.toml .
RUN pip install --no-cache-dir .
COPY sim_service/ sim_service/
CMD ["uvicorn", "sim_service.main:app", "--host", "0.0.0.0", "--port", "8000"]
