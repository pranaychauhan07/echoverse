FROM python:3.11-slim

# faster-whisper needs libsndfile/ffmpeg for some audio paths; piper needs
# libespeak-ng for phonemization.
RUN apt-get update && apt-get install -y --no-install-recommends \
    ffmpeg \
    espeak-ng \
    curl \
    && rm -rf /var/lib/apt/lists/*

RUN pip install --no-cache-dir uv

WORKDIR /app

COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-dev

COPY . .

# Piper voice models are large binaries, not committed to git -- fetch them
# at build time instead so a fresh `git clone` + `docker compose build`
# works on any machine without a manual setup step.
RUN mkdir -p voices && \
    for voice in en_US-lessac-medium en_US-amy-medium; do \
        speaker=$(echo "$voice" | cut -d- -f2); \
        base="https://huggingface.co/rhasspy/piper-voices/resolve/main/en/en_US/${speaker}/medium"; \
        curl -sL -o "voices/${voice}.onnx" "${base}/${voice}.onnx"; \
        curl -sL -o "voices/${voice}.onnx.json" "${base}/${voice}.onnx.json"; \
    done

ENV PATH="/app/.venv/bin:$PATH"
ENV PYTHONUNBUFFERED=1

EXPOSE 8000

CMD ["uv", "run", "uvicorn", "server:app", "--host", "0.0.0.0", "--port", "8000"]
