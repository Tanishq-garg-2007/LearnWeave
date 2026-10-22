# ==========================================
# Stage 1: Build Frontend SPA
# ==========================================
FROM node:20-slim AS frontend-builder
WORKDIR /build/frontend

# Copy package descriptors and install dependencies
COPY frontend/package*.json ./
RUN npm install

# Copy frontend source and build production assets
COPY frontend/ ./
RUN npm run build

# ==========================================
# Stage 2: Production Python Backend Runtime
# ==========================================
FROM python:3.11-slim

# Prevent Python from writing .pyc files and buffer stdout/stderr
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PORT=7860 \
    HOME=/home/user

# Install system dependencies (libsndfile for audio, curl for model downloads)
RUN apt-get update && apt-get install -y --no-install-recommends \
    libsndfile1 \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Hugging Face Spaces runs under UID 1000
RUN useradd -m -u 1000 user

WORKDIR /app

# Install Python dependencies
COPY backend/requirements.txt ./backend/
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r backend/requirements.txt

# Download Kokoro ONNX neural speech model and voices
RUN mkdir -p /app/models && \
    curl -L -o /app/models/kokoro-v1.0.onnx \
    "https://github.com/thewh1teagle/kokoro-onnx/releases/download/model-files-v1.0/kokoro-v1.0.onnx" && \
    curl -L -o /app/models/voices.bin \
    "https://github.com/thewh1teagle/kokoro-onnx/releases/download/model-files-v1.0/voices-v1.0.bin"

# Pre-cache FastEmbed sentence-transformers model (all-MiniLM-L6-v2)
RUN python -c "from fastembed import TextEmbedding; TextEmbedding(model_name='sentence-transformers/all-MiniLM-L6-v2')"

# Copy application backend code
COPY backend/ ./backend/

# Copy built frontend from Stage 1 into the location expected by main.py
COPY --from=frontend-builder /build/frontend/dist ./frontend/dist

# Copy entrypoint script and set permissions
COPY docker-entrypoint.sh ./docker-entrypoint.sh
RUN chmod +x ./docker-entrypoint.sh && \
    chown -R user:user /app /home/user

USER user

EXPOSE 7860

ENTRYPOINT ["/app/docker-entrypoint.sh"]
