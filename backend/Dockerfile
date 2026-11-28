FROM python:3.12-slim

# ── System dependencies ──────────────────────────────────────
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    build-essential \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# ── App directory ────────────────────────────────────────────
WORKDIR /app

# ── Python dependencies ───────────────────────────────────────
COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# ── Source code ───────────────────────────────────────────────
COPY . .

# ── Logs directory ────────────────────────────────────────────
RUN mkdir -p /var/log/market-intelligence

# ── Non-root user ────────────────────────────────────────────
RUN adduser --disabled-password --gecos "" appuser && \
    chown -R appuser:appuser /app /var/log/market-intelligence
USER appuser

EXPOSE 8000

# Default: run FastAPI (overridden in docker-compose for Celery)
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
