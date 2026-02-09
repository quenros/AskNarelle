#!/bin/bash

# 1. Start Flask (Backend)
# Navigate to backend directory
cd backend

echo "Starting Gunicorn (Flask)..."

# Run Gunicorn in the background (&)
# - Binds to 127.0.0.1:5000 (accessible only by Next.js in the same container)
# - Sends logs to stdout/stderr for Azure Log Stream visibility
# - Uses 1 worker to conserve memory on F1/B1 plans
gunicorn app:app \
    --bind 127.0.0.1:5000 \
    --workers 1 \
    --timeout 600 \
    --access-logfile - \
    --error-logfile - &

# 2. Start Next.js (Frontend)
# Navigate back to root then to frontend directory
cd ../frontend

# Azure provides the external port in the $PORT variable (e.g., 80 or 8080)
# Default to 3000 if not set (local testing)
SERVER_PORT=${PORT:-3000}

echo "Starting Next.js on port $SERVER_PORT..."

# Start Next.js in the foreground
# 'exec' ensures it becomes the main process to handle shutdown signals
exec npm run start -- -p $SERVER_PORT