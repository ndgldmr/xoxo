FROM python:3.11-slim

WORKDIR /app

COPY pyproject.toml .
COPY app/ app/
COPY scripts/ scripts/

RUN pip install --no-cache-dir .

EXPOSE 8080

CMD ["sh", "-c", "uvicorn app.api.routes:app --host 0.0.0.0 --port ${PORT:-8080}"]
