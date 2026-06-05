# Multi-stage build (docs/12 §2). Slim, non-root runtime, isolated venv.
FROM python:3.12-slim AS base
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PIP_DEFAULT_TIMEOUT=300 \
    PIP_RETRIES=10
WORKDIR /app

# --- builder: install runtime deps + the app into a venv ---
FROM base AS builder
ENV VIRTUAL_ENV=/opt/venv PATH=/opt/venv/bin:$PATH
# Bundled pip is fine; only setuptools+wheel are needed for the build backend.
# (Skipping the pip self-upgrade avoids an extra ~2 MB download on slow links.)
RUN python -m venv "$VIRTUAL_ENV" && pip install setuptools wheel
# Copy metadata + source BEFORE install so the package can build (pip needs app/).
COPY pyproject.toml ./
COPY app ./app
RUN pip install .

# --- runtime: copy the venv, run as non-root ---
FROM base AS runtime
ENV VIRTUAL_ENV=/opt/venv PATH=/opt/venv/bin:$PATH \
    DOCTR_CACHE_DIR=/home/forge/.cache/doctr
# OpenCV (a DocTR dep) needs libGL + glib at runtime; not present on python:slim.
RUN apt-get update \
    && apt-get install -y --no-install-recommends libgl1 libglib2.0-0 \
    && rm -rf /var/lib/apt/lists/*
COPY --from=builder /opt/venv /opt/venv
COPY app ./app
COPY alembic ./alembic
COPY alembic.ini ./
RUN useradd -m -u 10001 forge && mkdir -p /home/forge/.cache/doctr && chown -R forge /app /home/forge
USER forge
EXPOSE 8001
# API entrypoint; worker/beat override `command` in docker-compose / K8s.
CMD ["gunicorn", "app.main:app", "-k", "uvicorn.workers.UvicornWorker", "-b", "0.0.0.0:8001", "-w", "4", "--timeout", "120"]
