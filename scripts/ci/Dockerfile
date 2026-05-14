# CI build environment for osAfrica
# Tests AI core without models (uses mock inference server).

FROM debian:trixie-slim

RUN apt-get update && apt-get install -y --no-install-recommends \
    python3 python3-pip python3-venv python3-dev \
    build-essential cmake pkg-config \
    git curl \
    bubblewrap \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /workspace

# Install Python dependencies
COPY ai-core/pyproject.toml ai-core/pyproject.toml
RUN cd ai-core && pip install --break-system-packages ".[dev]" || true

# Copy source
COPY . .

# Install the package
RUN cd ai-core && pip install --break-system-packages -e ".[dev]"

# Default: run tests
CMD ["python3", "-m", "pytest", "ai-core/tests/", "-v", "--tb=short"]
