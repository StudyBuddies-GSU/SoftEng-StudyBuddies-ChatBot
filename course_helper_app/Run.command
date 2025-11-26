#!/bin/bash

# --- Auto-minimize Terminal window ---
osascript -e 'tell application "Terminal" to set miniaturized of front window to true'

# --- Ensure script runs from its own directory ---
cd "$(dirname "$0")"

echo "Checking if Docker Engine is running..."

# Check if Docker daemon is responding
docker info >/dev/null 2>&1

if [ $? -ne 0 ]; then
    echo "Docker is not running. Starting Docker Desktop..."

    # Start Docker Desktop (macOS)
    open -a Docker

    echo "Waiting for Docker Engine to start..."
    
    # Loop until Docker engine responds
    until docker info >/dev/null 2>&1; do
        sleep 2
    done
fi

echo "Docker Engine is running."

echo "Building Docker containers..."
docker compose build

if [ $? -ne 0 ]; then
  echo "Docker build failed. Press Enter to exit."
  read
  exit 1
fi

echo "Starting Docker containers..."
docker compose up &
UP_PID=$!

# Wait a bit before opening the browser
sleep 5

echo "Opening browser to http://localhost:8501 ..."
open "http://localhost:8501"

# Keep showing docker logs
wait "$UP_PID"


