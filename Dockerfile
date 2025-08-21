# Multi-stage build for smaller, more secure image
FROM python:3.11-slim as builder

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

# Install build dependencies
RUN apt-get update && apt-get install -y \
    build-essential \
    git \
    && rm -rf /var/lib/apt/lists/*

# Create virtual environment
RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

# Upgrade pip and install wheel
RUN pip install --upgrade pip setuptools wheel

# Copy requirements and install Python dependencies
COPY requirements.txt requirements-frozen.txt ./
RUN pip install --no-cache-dir -r requirements-frozen.txt

# Production stage
FROM python:3.11-slim

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PATH="/opt/venv/bin:$PATH" \
    TAILSENTRY_ENV=production

# Install runtime dependencies only
RUN apt-get update && apt-get install -y \
    curl \
    ca-certificates \
    && rm -rf /var/lib/apt/lists/* \
    && apt-get clean

# Create non-root user for security
RUN groupadd -r tailsentry && useradd -r -g tailsentry tailsentry

# Copy virtual environment from builder stage
COPY --from=builder /opt/venv /opt/venv

# Set working directory
WORKDIR /app

# Copy application code (excluding unnecessary files)
COPY --chown=tailsentry:tailsentry *.py ./
COPY --chown=tailsentry:tailsentry routes/ ./routes/
COPY --chown=tailsentry:tailsentry templates/ ./templates/
COPY --chown=tailsentry:tailsentry static/ ./static/
COPY --chown=tailsentry:tailsentry middleware/ ./middleware/
COPY --chown=tailsentry:tailsentry services/ ./services/
COPY --chown=tailsentry:tailsentry config/ ./config/

# Create necessary directories with proper permissions
RUN mkdir -p /app/logs /app/data /app/config && \
    chown -R tailsentry:tailsentry /app

# Switch to non-root user
USER tailsentry

# Create default configuration if not present
RUN if [ ! -f /app/config/tailsentry_config.json ]; then \
    echo '{"host": "0.0.0.0", "port": 8080, "debug": false}' > /app/config/tailsentry_config.json; \
    fi

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=30s --retries=3 \
    CMD curl -f http://localhost:8080/ || exit 1

# Expose port
EXPOSE 8080

# Run application
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8080", "--workers", "1"]
