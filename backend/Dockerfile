# syntax=docker/dockerfile:1
# Multi-stage build (docs/12 §2). Slim, non-root runtime, isolated venv.
#
# Layer caching: third-party deps are installed in a layer keyed ONLY on pyproject.toml,
# so editing application source never re-downloads/re-builds torch/doctr/etc. A BuildKit
# pip cache mount (--mount=type=cache) keeps downloaded wheels across builds, so even a
# deps change (new pyproject) doesn't re-download what it already has.
FROM python:3.12-slim AS base
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PIP_DEFAULT_TIMEOUT=300 \
    PIP_RETRIES=10
WORKDIR /app

# --- builder: install runtime deps + the app into a venv ---
FROM base AS builder
ENV VIRTUAL_ENV=/opt/venv PATH=/opt/venv/bin:$PATH
# Bundled pip is fine; only setuptools+wheel are needed for the build backend.
RUN python -m venv "$VIRTUAL_ENV" && pip install setuptools wheel

# 1) Dependencies only. A stub package lets the build backend resolve+install every
#    third-party dep from pyproject.toml WITHOUT the real source — so this heavy layer
#    is cached as long as pyproject.toml is unchanged.
COPY pyproject.toml ./
RUN mkdir -p app && touch app/__init__.py
RUN --mount=type=cache,target=/root/.cache/pip pip install .

# 2) The real app on top, --no-deps so nothing third-party is touched. This is the only
#    layer that reruns on a code change, and it takes ~seconds.
COPY app ./app
RUN --mount=type=cache,target=/root/.cache/pip pip install --no-deps --force-reinstall .

# --- runtime: copy the venv, run as non-root ---
FROM base AS runtime
ENV VIRTUAL_ENV=/opt/venv PATH=/opt/venv/bin:$PATH \
    DOCTR_CACHE_DIR=/home/forge/.cache/doctr
# OpenCV (a DocTR dep) needs libGL + glib at runtime; not present on python:slim.
RUN --mount=type=cache,target=/var/cache/apt,sharing=locked \
    --mount=type=cache,target=/var/lib/apt,sharing=locked \
    apt-get update \
    && apt-get install -y --no-install-recommends libgl1 libglib2.0-0
COPY --from=builder /opt/venv /opt/venv
COPY app ./app
COPY alembic ./alembic
COPY alembic.ini ./
RUN useradd -m -u 10001 forge && mkdir -p /home/forge/.cache/doctr && chown -R forge /app /home/forge
USER forge
EXPOSE 8001
# API entrypoint; worker/beat override `command` in docker-compose / K8s.
# --timeout 360 (> FORGE_OCR_LLM_TIMEOUT_S=300) so a slow local-LLM label scan isn't killed mid-request.
CMD ["gunicorn", "app.main:app", "-k", "uvicorn.workers.UvicornWorker", "-b", "0.0.0.0:8001", "-w", "4", "--timeout", "360"]
