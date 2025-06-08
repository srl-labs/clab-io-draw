FROM debian:12-slim

# Install build tools and required libraries
RUN apt-get update && apt-get install -y --no-install-recommends \
    python3.11 \
    python3.11-dev \
    python3.11-distutils \
    python3-pip \
    build-essential \
    curl \
    ca-certificates \
    # X11 and graphics support for headless draw.io
    xvfb \
    xauth \
    libgtk-3-0 \
    # Additional libraries required for draw.io AppImage/Electron
    libnss3 \
    libatk-bridge2.0-0 \
    libdrm2 \
    libxcomposite1 \
    libxdamage1 \
    libxrandr2 \
    libgbm1 \
    libxss1 \
    libasound2 \
    libatspi2.0-0 \
    libgtk-3-0 \
    libgdk-pixbuf2.0-0 \
  && rm -rf /var/lib/apt/lists/*

# Pre-install draw.io AppImage so it doesn't need to be downloaded at runtime
ARG DRAWIO_VERSION=27.0.9
RUN curl -L \
    -o /opt/drawio.AppImage \
    "https://github.com/jgraph/drawio-desktop/releases/download/v${DRAWIO_VERSION}/drawio-x86_64-${DRAWIO_VERSION}.AppImage" \
    && chmod +x /opt/drawio.AppImage
ENV DRAWIO_BIN=/opt/drawio.AppImage

# Install uv
RUN curl -LsSf https://astral.sh/uv/install.sh | sh
ENV PATH="/root/.local/bin:${PATH}"

# Set terminal environment variables
ENV TERM=xterm-256color
ENV COLORTERM=truecolor

# Set up working directory
WORKDIR /app

COPY pyproject.toml ./
COPY src/ ./src/
COPY entrypoint.sh ./

# Create virtual environment and install dependencies using uv
RUN --mount=type=cache,target=/root/.cache/pip \
    --mount=type=cache,target=/root/.cache/uv \
    uv venv /opt/venv && \
    uv pip install --python /opt/venv/bin/python -e .

# Make the entrypoint script executable
RUN chmod +x /app/entrypoint.sh

# Update PATH to use virtual environment
ENV PATH="/opt/venv/bin:${PATH}"

# Set the working directory for running the application
WORKDIR /data
# Set APP_BASE_DIR to the installed package location so Grafana templates
# and config files are found during runtime
ENV APP_BASE_DIR=/app/src/clab_io_draw

# Use the entrypoint script to handle script execution
ENTRYPOINT ["/app/entrypoint.sh"]