# Base image
FROM python:3.13-slim

# Prevent Python from writing .pyc files and buffer stdout/stderr for clean logs
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

# Set clean root working directory
WORKDIR /app

# System dependencies needed for compiling native wheels (e.g., ChromaDB/hnswlib)
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# 1. Copy ONLY requirements first to leverage Docker layer caching
COPY requirements.txt .

# Install lightweight CPU-only PyTorch first (saves ~2.5GB of RAM/disk), then project deps
RUN pip install --no-cache-dir torch --index-url https://download.pytorch.org/whl/cpu && \
    pip install --no-cache-dir -r requirements.txt

# 2. Copy the rest of the codebase
COPY . .

EXPOSE 8000

# IMPORTANT: Use "app:app" if your FastAPI file is app.py in root,
# or "src.api.main:app" if it is located at src/api/main.py
CMD ["sh", "-c", "uvicorn src.api.main:app --host 0.0.0.0 --port ${PORT:-8000}"]




















# # Base image
# FROM python:3.13-slim

# # Working directory
# WORKDIR /src

# # 1. Copy ONLY requirements first to leverage Docker layer caching
# COPY requirements.txt .

# # Install dependencies
# RUN pip install --no-cache-dir -r requirements.txt


# # 2. Copy the rest of the codebase afterwards
# COPY . .

# # Expose port (Documentation only, Render ignores EXPOSE)
# EXPOSE 8000


# CMD sh -c "uvicorn src.api.main:app --host 0.0.0.0 --port ${PORT:-8000}"