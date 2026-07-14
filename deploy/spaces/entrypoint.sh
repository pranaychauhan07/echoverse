#!/usr/bin/env bash
# Starts the local Ollama daemon (its model is already baked into this
# image at build time -- see deploy/spaces/Dockerfile), waits for it to
# be ready, then starts the API in the foreground.
set -e

ollama serve &

until curl -sf http://127.0.0.1:11434/api/version >/dev/null 2>&1; do
    echo "Waiting for Ollama to start..."
    sleep 1
done

exec uv run uvicorn server:app --host 0.0.0.0 --port 8000
