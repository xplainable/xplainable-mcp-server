# Multi-stage build for security and size optimization
FROM python:3.11-slim as builder

# Set working directory
WORKDIR /app

# Install build dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# Copy build files
COPY pyproject.toml README.md ./

# Create virtual environment and install dependencies
RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir .

# Final stage
FROM python:3.11-slim

# Create non-root user
RUN groupadd -g 1000 mcp && \
    useradd -r -u 1000 -g mcp mcp

# Set working directory
WORKDIR /app

# Copy virtual environment from builder
COPY --from=builder /opt/venv /opt/venv

# Copy application code
COPY --chown=mcp:mcp xplainable_mcp/ ./xplainable_mcp/

# Set environment variables
ENV PATH="/opt/venv/bin:$PATH" \
    PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1

# Switch to non-root user
USER mcp

# Health check (uses /health endpoint in HTTP mode)
HEALTHCHECK --interval=30s --timeout=10s --start-period=10s --retries=3 \
    CMD python -c "import httpx; httpx.get('http://localhost:8000/health').raise_for_status()" || exit 1

# Expose port
EXPOSE 8000

# Default to HTTP transport via ASGI
ENV MCP_TRANSPORT="streamable-http"

# Run with uvicorn for production
CMD ["uvicorn", "xplainable_mcp.asgi:app", "--host", "0.0.0.0", "--port", "8000"]