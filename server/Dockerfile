FROM python:3.11-slim

# dify-hub backend. Runs the FastAPI app from source (PYTHONPATH=/app), so the
# Alembic config + migrations under /app resolve correctly at startup.
WORKDIR /app
ENV PYTHONUNBUFFERED=1 \
    PYTHONPATH=/app \
    PIP_NO_CACHE_DIR=1

# Runtime dependencies — keep in sync with [project].dependencies in pyproject.toml.
RUN pip install --no-cache-dir \
    "fastapi>=0.115" \
    "uvicorn>=0.30" \
    "sqlalchemy>=2.0" \
    "httpx>=0.27" \
    "pydantic>=2.7" \
    "pydantic-settings>=2.2" \
    "python-dotenv>=1.0" \
    "cryptography>=42" \
    "alembic>=1.13" \
    "python-multipart>=0.0.9"

COPY app ./app
COPY migrations ./migrations
COPY alembic.ini ./alembic.ini
COPY scripts ./scripts

EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
