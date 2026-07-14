# EchoVerse

An agentic, $0-to-run audiobook creation pipeline: text in, narrated audio
out, entirely on local/open-source models — no API keys, no cloud bill.

Unlike a simple text-to-speech script, EchoVerse is a multi-agent system
built on [LangGraph](https://github.com/langchain-ai/langgraph):

```
Intake -> Rewriter <-> Critic (revision loop)
       -> Voice-Casting (narrator vs. dialogue)
       -> TTS <-> Audio-QA (re-transcribe + diff, retries on failure)
```

The Critic agent scores every rewrite for meaning/tone/safety and sends it
back for revision if it falls short. The Audio-QA agent re-transcribes the
generated narration with Whisper and diffs it against the script, forcing
a re-synthesis if the audio doesn't actually match the text. Both loops
have been observed firing for real in testing, not just in theory.

## Stack (all $0)

- **LLM**: [Ollama](https://ollama.com) running `llama3.2:3b` locally
- **TTS**: [Piper](https://github.com/rhasspy/piper) (local, CPU-friendly)
- **Audio QA**: [faster-whisper](https://github.com/SYSTRAN/faster-whisper) (local)
- **Orchestration**: [LangGraph](https://github.com/langchain-ai/langgraph)
- **API**: FastAPI, async job queue backed by SQLite
- **Deploy**: Docker Compose, designed for Oracle Cloud's Always-Free ARM tier (see [DEPLOY.md](DEPLOY.md))

## Local setup

```bash
# 1. Install Python 3.11 + deps (uv manages both)
uv sync

# 2. Pull the LLM
ollama pull llama3.2:3b

# 3. Fetch the Piper voice models (not committed to git -- large binaries)
bash scripts/download_voices.sh

# 4. Try it via the CLI
uv run python main.py --text "Your story here." --tone suspenseful

# ...or run the API
uv run uvicorn server:app --reload
```

## API

```
POST /jobs            {"text": "...", "tone": "neutral|suspenseful|inspiring"} -> {job_id}
POST /jobs/upload      multipart file upload + tone
GET  /jobs/{id}        job status + full result (rewrite, transcript, QA score, revision log)
GET  /jobs/{id}/audio  download the narration
GET  /jobs             history (persists across restarts)
GET  /stats            aggregate usage: chars processed, avg latency, revision/retry counts
```

## Evals

```bash
uv run python evals/run_evals.py
```

Runs a small golden set through the Rewriter+Critic loop and checks
against minimum quality bars — a regression check for when models or
prompts change.

## Deploying

See [DEPLOY.md](DEPLOY.md) — the whole stack (including the LLM) runs on
Oracle Cloud's Always Free tier for genuinely $0/month.
