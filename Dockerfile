FROM python:3.11-slim

# Install build tools and required libraries
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    python3-dev \
    curl \
  && rm -rf /var/lib/apt/lists/*

# Install uv
RUN curl -LsSf https://astral.sh/uv/install.sh | sh
ENV PATH="/root/.local/bin:${PATH}"

# Set up working directory
WORKDIR /app

COPY pyproject.toml ./
COPY drawio2clab.py ./
COPY clab2drawio.py ./
COPY entrypoint.sh ./
COPY styles/ ./styles/
COPY core/ ./core/
COPY cli/ ./cli/

# Install dependencies using uv
RUN --mount=type=cache,target=/root/.cache/pip \
    --mount=type=cache,target=/root/.cache/uv \
    uv pip sync --system pyproject.toml

# Make the entrypoint script executable
RUN chmod +x /app/entrypoint.sh

# Set the working directory for running the application
WORKDIR /data
ENV APP_BASE_DIR=/app

# Use the entrypoint script to handle script execution
ENTRYPOINT ["/app/entrypoint.sh"]