# Stew: The Helmholtz AI Data Steward
# Compatible with Hugging Face Spaces (port 7860, user 1000) & Helmholtz Cloud (port 8000)
FROM python:3.12-slim

WORKDIR /app

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PORT=7860

# Install minimal OS dependencies for scientific libraries
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Set up user with UID 1000 (Required for Hugging Face Spaces non-root execution)
RUN useradd -m -u 1000 user && \
    mkdir -p /app/data_store && \
    chown -R user:user /app

COPY --chown=user:user requirements.txt .
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

COPY --chown=user:user . .

USER user
ENV HOME=/home/user \
    PATH=/home/user/.local/bin:$PATH

EXPOSE 7860

# Healthcheck endpoint
HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
  CMD curl -f http://localhost:${PORT}/api/status || exit 1

CMD ["sh", "-c", "uvicorn clara.api.server:app --host 0.0.0.0 --port ${PORT:-7860}"]
