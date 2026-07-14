---
title: EchoVerse
emoji: 🎧
colorFrom: purple
colorTo: pink
sdk: docker
app_port: 8000
pinned: false
---

# EchoVerse

An agentic, $0-to-run audiobook narration pipeline — local LLM (Ollama),
local TTS (Piper), local audio QA (faster-whisper), orchestrated as a
LangGraph multi-agent system with self-correcting revision loops.

See the main repo for full details: https://github.com/pranaychauhan07/echoverse

## Try it

```bash
curl -X POST https://<this-space-url>/jobs \
  -H "Content-Type: application/json" \
  -d '{"text": "Your story here.", "tone": "suspenseful"}'

curl https://<this-space-url>/jobs/<job_id>
curl https://<this-space-url>/jobs/<job_id>/audio -o narration.wav
```

**Note on this Space's free tier**: storage is ephemeral, so job history
resets on restart/sleep-wake. The LLM model itself is baked into the
Docker image at build time, so a fresh wake-up doesn't need to
re-download it.
