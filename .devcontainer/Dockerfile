FROM python:3.12-slim
# System dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl build-essential git libffi-dev tree ca-certificates && \
    rm -rf /var/lib/apt/lists/*

# Install uv
RUN curl -Ls https://astral.sh/uv/install.sh | bash

# Add uv to PATH
ENV PATH="/root/.local/bin:$PATH"

WORKDIR /workspace

# Copy requirements
COPY pyproject.toml uv.lock ./

# Copy source
COPY src ./src

# Explicitly add /usr/local/bin to PATH for this build stage
ENV PATH="/usr/local/bin:$PATH"

# Install dependencies
RUN uv pip install -r pyproject.toml --system .[dev]

# Setup Pythonpath for src directory to prevent headaches with imports
# This is necessary for the src directory to be recognized as a package
ENV PYTHONPATH=/workspace/src

# Verify python and uv versions as a sanity check
RUN python --version && uv --version
