# Stew: The Helmholtz Data Steward Container
FROM python:3.12-slim

WORKDIR /app

# Prevent Python from writing .pyc files to disk and buffering stdout/stderr
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PORT=8000 \
    HOST=0.0.0.0

# Install minimal OS dependencies for scientific libraries
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Install Python requirements
COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# Copy source code and assets
COPY . .

# Ensure storage directory exists
RUN mkdir -p /app/data_store

EXPOSE 8000

# Healthcheck endpoint
HEALTHCHECK --interval=30s --timeout=5s --start-period=5s --retries=3 \
  CMD curl -f http://localhost:8000/api/status || exit 1

CMD ["uvicorn", "clara.api.server:app", "--host", "0.0.0.0", "--port", "8000"]
