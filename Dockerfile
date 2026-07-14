# Combined single-container build for Hugging Face Spaces (Docker SDK).
#
# Spaces' free CPU tier has ephemeral runtime storage (resets on
# restart/sleep-wake), so unlike docker-compose.yml's two-service setup
# (app + ollama, with a persistent named volume for pulled models), this
# bakes the LLM weights directly into the image at build time. That way a
# Space waking from sleep doesn't need to re-download ~2GB before it can
# serve a request.

FROM python:3.11-slim

RUN apt-get update && apt-get install -y --no-install-recommends \
    ffmpeg \
    espeak-ng \
    curl \
    ca-certificates \
    && rm -rf /var/lib/apt/lists/*

# Install Ollama itself (not just the Python client) since this container
# has to run the inference server too -- there's no separate `ollama`
# service to talk to here.
RUN curl -fsSL https://ollama.com/install.sh | sh

RUN pip install --no-cache-dir uv

WORKDIR /app

COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-dev

COPY . .

# Piper voice models -- same rationale as the main Dockerfile: not
# committed to git, fetched at build time.
RUN mkdir -p voices && \
    for voice in en_US-lessac-medium en_US-amy-medium; do \
        speaker=$(echo "$voice" | cut -d- -f2); \
        base="https://huggingface.co/rhasspy/piper-voices/resolve/main/en/en_US/${speaker}/medium"; \
        curl -sL -o "voices/${voice}.onnx" "${base}/${voice}.onnx"; \
        curl -sL -o "voices/${voice}.onnx.json" "${base}/${voice}.onnx.json"; \
    done

# Bake the LLM into the image: start the daemon, pull the model into it
# (which writes into this build layer), then stop the daemon -- the
# weights persist in the image regardless of Spaces' ephemeral storage.
RUN ollama serve & \
    sleep 5 && \
    ollama pull llama3.2:3b && \
    kill %1

ENV PATH="/app/.venv/bin:$PATH"
ENV PYTHONUNBUFFERED=1
ENV OLLAMA_HOST=http://127.0.0.1:11434

# Hugging Face Spaces routes traffic to the port declared as `app_port`
# in this repo's README.md frontmatter -- keep them in sync.
EXPOSE 8000

RUN chmod +x entrypoint.sh
CMD ["./entrypoint.sh"]
