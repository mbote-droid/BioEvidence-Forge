FROM python:3.12-slim AS runtime

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app

RUN groupadd --system service && useradd --system --gid service service

COPY pyproject.toml README.md ./
COPY src ./src

RUN pip install --no-cache-dir . && \
    mkdir -p /app/data /app/reports && \
    chown -R service:service /app

USER service

EXPOSE 8080

HEALTHCHECK --interval=30s --timeout=5s --start-period=15s --retries=3 \
  CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8080/health', timeout=3)"

CMD ["uvicorn", "bioevidence.api:create_app", "--factory", "--host", "0.0.0.0", "--port", "8080"]

