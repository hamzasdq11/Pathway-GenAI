# Multi-stage build to reduce final image size
FROM python:3.11-slim AS builder

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    DEBIAN_FRONTEND=noninteractive

# System deps needed to compile some python packages
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc g++ python3-dev build-essential pkg-config libpq-dev libmariadb-dev curl \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Copy minimal files needed for dependency install
COPY requirements.txt README.md ./

# Create a virtualenv and install deps into it
RUN python -m venv /opt/venv \
 && /opt/venv/bin/pip install --upgrade pip \
 && /opt/venv/bin/pip install --no-cache-dir -r requirements.txt

# ----- Runtime image -----
FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONPATH=/app \
    DEBIAN_FRONTEND=noninteractive \
    PATH="/opt/venv/bin:$PATH"

WORKDIR /app

# Only runtime shared libs
RUN apt-get update && apt-get install -y --no-install-recommends \
    libpq5 libmariadb3 curl \
    && rm -rf /var/lib/apt/lists/*

# Bring in the prebuilt virtualenv
COPY --from=builder /opt/venv /opt/venv

# App code
COPY . .

# Non-root user
RUN groupadd -r appuser && useradd -r -g appuser appuser && chown -R appuser:appuser /app
USER appuser

EXPOSE 8000

# Start the app (change if your entry differs)
CMD ["python", "-m", "fincept_terminal.FinceptTerminalStart"]
