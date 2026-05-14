# syntax=docker/dockerfile:1.7

# ---- Tectonic binary ----------------------------------------------------
FROM debian:bookworm-slim AS tectonic
ARG TECTONIC_VERSION=0.16.9
RUN apt-get update && apt-get install -y --no-install-recommends \
        ca-certificates curl xz-utils \
    && rm -rf /var/lib/apt/lists/*
RUN curl -fsSL "https://github.com/tectonic-typesetting/tectonic/releases/download/tectonic@${TECTONIC_VERSION}/tectonic-${TECTONIC_VERSION}-x86_64-unknown-linux-musl.tar.gz" \
    | tar -xz -C /usr/local/bin tectonic

# ---- Python deps --------------------------------------------------------
FROM ghcr.io/astral-sh/uv:python3.13-bookworm-slim AS deps
WORKDIR /app
COPY pyproject.toml uv.lock* ./
RUN uv sync --frozen --no-dev --no-install-project || uv sync --no-dev --no-install-project

# ---- Runtime ------------------------------------------------------------
FROM python:3.13-slim-bookworm
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PATH="/app/.venv/bin:$PATH" \
    PORT=8080

RUN apt-get update && apt-get install -y --no-install-recommends \
        ca-certificates fontconfig \
    && rm -rf /var/lib/apt/lists/*

COPY --from=tectonic /usr/local/bin/tectonic /usr/local/bin/tectonic
COPY --from=deps /app/.venv /app/.venv

WORKDIR /app
COPY app ./app

EXPOSE 8080
CMD ["sh", "-c", "uvicorn app.main:app --host 0.0.0.0 --port ${PORT}"]
