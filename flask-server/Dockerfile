# syntax=docker/dockerfile:1.7
FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

WORKDIR /flask-backend

# System packages
RUN apt-get update && apt-get install -y --no-install-recommends \
      libmagic1 libgl1 libglib2.0-0 \
  && rm -rf /var/lib/apt/lists/*

# --- CACHE FRIENDLY DEPENDENCIES ---
COPY requirements.txt /tmp/requirements.txt
RUN --mount=type=cache,target=/root/.cache/pip \
    pip install --no-cache-dir -r /tmp/requirements.txt

# --- APP CODE AFTER DEPS ---
COPY app.py ai_search_helper.py blob_storage_helper.py common_helper.py mongo_helper.py course_share_helper.py /flask-backend/

EXPOSE 5000
CMD ["gunicorn", "app:app", "-b", "0.0.0.0:5000", "-w", "4", "--timeout", "600"]
