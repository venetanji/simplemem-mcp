FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && \
    apt-get install -y --no-install-recommends curl && \
    rm -rf /var/lib/apt/lists/*

# Install uv for fast package management
RUN pip install --no-cache-dir uv

# Copy project files
COPY pyproject.toml README.md ./
COPY src ./src

# Install the package and dependencies using uv
RUN uv pip install --system .

# Create directory for OAuth storage
RUN mkdir -p /root/.simplemem-mcp/oauth && chmod 700 /root/.simplemem-mcp

# Expose ports
# 3333 for MCP HTTP transports (streamable-http/sse)
EXPOSE 3333

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
  CMD curl -f http://localhost:3333/health || exit 1

# Default command: run MCP server with streamable-http transport
# Override with docker-compose or docker run commands as needed
CMD ["simplemem-mcp", "--oauth-required", "--transport",  "streamable-http", "--host", "0.0.0.0", "--port", "3333"]
