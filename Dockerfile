# Multi-stage builder
FROM python:3.11-slim as builder

WORKDIR /app

# Install build dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    libffi-dev \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first (for better caching)
COPY requirements.txt /app/requirements.txt

# Install Python dependencies
RUN pip install --no-cache-dir --user -r /app/requirements.txt

# Copy source code
COPY luminamind /app/luminamind
COPY scripts /app/scripts
COPY pyproject.toml /app/

# Production stage
FROM python:3.11-slim

WORKDIR /app

# Copy installed packages from builder
COPY --from=builder /root/.local /root/.local
COPY --from=builder /app/luminamind /app/luminamind
COPY --from=builder /app/scripts /app/scripts

# Set PATH for user binaries
ENV PATH=/root/.local/bin:$PATH

# Create non-root user
RUN useradd -m luminamind && \
    chown -R luminamind:luminamind /app
USER luminamind

# Expose ports
EXPOSE 8000 8080 9090

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

# Default command
CMD ["python", "-m", "luminamind.api"]
