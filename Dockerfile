# Use the smallest possible Python base
FROM python:3.11-slim-bookworm AS builder

# Install minimal build dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    curl \
    ca-certificates \
    && rm -rf /var/lib/apt/lists/*

# Install uv for faster dependency resolution
RUN curl -LsSf https://astral.sh/uv/install.sh | sh
ENV PATH="/root/.local/bin:${PATH}"

WORKDIR /app
COPY pyproject.toml ./
COPY src/ ./src/

# Install dependencies
RUN uv venv /opt/venv && \
    uv pip install --python /opt/venv/bin/python -e .

FROM python:3.11-slim-bookworm

COPY --from=builder /opt/venv /opt/venv
COPY --from=builder /app/src /app/src
COPY entrypoint.sh /app/

ENV PATH="/opt/venv/bin:${PATH}"
ENV APP_BASE_DIR=/app/src/clab_io_draw
ENV TERM=xterm-256color
ENV COLORTERM=truecolor
ENV IN_DOCKER=true
ENV HOME=/root

RUN chmod +x /app/entrypoint.sh

WORKDIR /data
ENTRYPOINT ["/app/entrypoint.sh"]
