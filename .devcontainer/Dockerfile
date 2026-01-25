# Easy Track Brownie Development Container
# Platform linux/amd64 required for prebuilt solc 0.8.6

FROM --platform=linux/amd64 python:3.10-slim-bookworm

ARG POETRY_VERSION=1.8.2
ARG NODE_MAJOR=18

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    POETRY_VIRTUALENVS_CREATE=false \
    POETRY_NO_INTERACTION=1

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    git \
    curl \
    build-essential \
    libssl-dev \
    libffi-dev \
    ca-certificates \
    gnupg \
    && rm -rf /var/lib/apt/lists/*

# Install Node.js (required for Hardhat fork testing)
RUN curl -fsSL https://deb.nodesource.com/gpgkey/nodesource-repo.gpg.key \
    | gpg --dearmor -o /usr/share/keyrings/nodesource.gpg \
    && echo "deb [signed-by=/usr/share/keyrings/nodesource.gpg] https://deb.nodesource.com/node_${NODE_MAJOR}.x nodistro main" \
    > /etc/apt/sources.list.d/nodesource.list \
    && apt-get update \
    && apt-get install -y --no-install-recommends nodejs \
    && rm -rf /var/lib/apt/lists/* \
    && corepack enable

# Install Poetry from PyPI at the pinned version
RUN pip install --no-cache-dir "poetry==${POETRY_VERSION}"

WORKDIR /workspace

# Copy and install dependencies (these layers are cached until lock files change)
COPY pyproject.toml poetry.lock* ./
RUN poetry install --no-root

COPY package.json package-lock.json* ./
RUN corepack prepare npm@10.5.0 --activate \
    && if [ -f package-lock.json ]; then \
      npm ci --ignore-scripts; \
    else \
      npm install --ignore-scripts; \
    fi

CMD ["/bin/bash"]