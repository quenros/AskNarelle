# syntax=docker/dockerfile:1.7
FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

WORKDIR /flask-backend

# System packages (one layer, slim, cleaned)
RUN apt-get update && apt-get install -y --no-install-recommends \
      libmagic1 libgl1-mesa-glx libglib2.0-0 \
  && rm -rf /var/lib/apt/lists/*

# --- CACHE FRIENDLY DEPENDENCIES ---
# Only copy the lock/requirements first so this layer is reused
COPY requirements.txt /tmp/requirements.txt

# Use BuildKit cache for pip (MUCH faster after first build)
RUN --mount=type=cache,target=/root/.cache/pip \
    pip install -r /tmp/requirements.txt

# --- APP CODE AFTER DEPS ---
# Copy source (don’t copy .env; pass at runtime)
COPY app.py ai_search_helper.py blob_storage_helper.py common_helper.py mongo_helper.py course_share_helper.py /flask-backend/

# Keep ports consistent with your command
EXPOSE 5000

# Gunicorn (prod style). For dev, override command with --reload (see below).
CMD ["gunicorn", "app:app", "-b", "0.0.0.0:5000", "-w", "4", "--timeout", "600"]
