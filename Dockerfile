# =============================================================================
# Semptify FastAPI - Production Dockerfile
# =============================================================================
# Multi-stage build for optimal image size and security
# 
# Build: docker build -t semptify:latest .
# Run:   docker run -p 8000:8000 --env-file .env semptify:latest
# =============================================================================

# -----------------------------------------------------------------------------
# Stage 1: Builder - Install dependencies
# -----------------------------------------------------------------------------
FROM python:3.11-slim AS builder

WORKDIR /app

# Install build dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    gcc \
    libffi-dev \
    libpq-dev \
    libmagic1 \
    && rm -rf /var/lib/apt/lists/*

# Create virtual environment
RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

# Copy requirements first for better caching.
# Uses requirements-render-mvp.txt — the trimmed production set. The full
# requirements.txt adds ~1.5GB of sentence-transformers/torch plus playwright
# and dev tooling that the render_mvp profile never loads (embedding model is
# lazy-gated off; playwright import is graceful). Revert to requirements.txt
# if the deploy target is ever switched to the full profile.
COPY requirements-render-mvp.txt .

# Install Python dependencies
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements-render-mvp.txt

# -----------------------------------------------------------------------------
# Stage 2: Runtime - Minimal production image
# -----------------------------------------------------------------------------
FROM python:3.11-slim AS runtime

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PORT=8000

# Set work directory
WORKDIR /app

# Install runtime dependencies only
RUN apt-get update && apt-get install -y --no-install-recommends \
    libpq5 \
    curl \
    libmagic1 \
    libcairo2 \
    libpango-1.0-0 \
    libpangocairo-1.0-0 \
    tesseract-ocr \
    tesseract-ocr-eng \
    && rm -rf /var/lib/apt/lists/* \
    && apt-get clean

# Copy virtual environment from builder
COPY --from=builder /opt/venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

# Create non-root user for security
RUN groupadd --gid 1000 semptify && \
    useradd --uid 1000 --gid semptify --shell /bin/bash --create-home semptify

# Cache-bust: forces fresh COPY on every deploy
ARG CACHEBUST=2024-06-09-v2
# Copy application code
COPY --chown=semptify:semptify . .

# Create runtime directories
RUN mkdir -p uploads uploads/vault logs security data data/inventory && \
    chown -R semptify:semptify uploads logs security data data

# Bake the embedding model weights into the image. fastembed's ONNX build
# of all-MiniLM-L6-v2 (~90MB) downloads at build time into a shared cache
# the non-root user can read; LOCAL_FILES_ONLY stops any runtime egress —
# if the weights are ever missing, load fails fast instead of fetching.
ENV EMBEDDING_CACHE_DIR=/opt/fastembed-cache \
    EMBEDDING_MODEL_LOCAL_FILES_ONLY=true
RUN python -c "from fastembed import TextEmbedding; TextEmbedding('sentence-transformers/all-MiniLM-L6-v2', cache_dir='/opt/fastembed-cache')" && \
    chown -R semptify:semptify /opt/fastembed-cache

# Switch to non-root user
USER semptify

# Precompile Python bytecode so cold starts on Render's shared CPU skip
# per-file compilation. PYTHONDONTWRITEBYTECODE only blocks writing .pyc;
# the precompiled files are still read and used at runtime.
RUN python -m compileall -q /app/app

# Expose port (Render sets PORT env var, defaults to 8000)
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:${PORT}/health || exit 1

# Start command - uses $PORT env var for Render compatibility
# --proxy-headers + --forwarded-allow-ips: all Render traffic arrives via their
# edge proxy; without these uvicorn sees http/<proxy-IP> instead of
# https/<client-IP>. The app already trusts X-Forwarded-For manually for rate
# limiting and jurisdiction, so this changes no security assumption.
# Note: migrations are handled by the app's lifespan startup (Stage 3b) which
# catches errors gracefully. Running alembic in CMD would fail the deploy on
# partial migrations (schema drift). The app itself runs alembic on startup.
CMD ["sh", "-c", "uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000} --workers 1 --proxy-headers --forwarded-allow-ips '*'"]
