FROM python:3.12-slim
# System dependencies (adjust as needed)
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl build-essential git libffi-dev tree ca-certificates && \
    rm -rf /var/lib/apt/lists/*

# Install uv
RUN curl -Ls https://astral.sh/uv/install.sh | bash

# Add uv to PATH
ENV PATH="/root/.local/bin:$PATH"

# Copy your requirements
COPY pyproject.toml pyproject.toml


# Explicitly add /usr/local/bin to PATH for this build stage
ENV PATH="/usr/local/bin:$PATH"

# Install dependencies
RUN uv pip install -r pyproject.toml --system
