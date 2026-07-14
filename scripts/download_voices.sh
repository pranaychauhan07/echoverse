#!/usr/bin/env bash
# Fetches the Piper voice models used for local narration + dialogue casting.
# Not committed to git (large binaries) -- run this once after cloning.
set -euo pipefail

cd "$(dirname "$0")/../voices"

for voice in en_US-lessac-medium en_US-amy-medium; do
    speaker="${voice#en_US-}"
    speaker="${speaker%-medium}"
    base="https://huggingface.co/rhasspy/piper-voices/resolve/main/en/en_US/${speaker}/medium"
    echo "Fetching ${voice}..."
    curl -sL -o "${voice}.onnx" "${base}/${voice}.onnx"
    curl -sL -o "${voice}.onnx.json" "${base}/${voice}.onnx.json"
done

echo "Done. Voices in $(pwd):"
ls -la ./*.onnx
