# Deploying EchoVerse — Oracle Cloud Always Free

This gets the full stack (FastAPI + Ollama + Piper + Whisper, all local
inference) running on a real public server for **$0/month, indefinitely**.
Oracle's "Always Free" ARM tier (Ampere A1: up to 4 OCPU / 24GB RAM) is
the only free-tier option with enough RAM to run a local LLM properly —
this has been tested locally via the same `docker-compose.yml` and works.

Because everything is containerized, this is not locked to Oracle: the
exact same `docker-compose.yml` runs on any VM (a paid droplet, AWS, your
own hardware) if you ever want to move later — moving hosts is a redeploy,
not a rewrite.

## 1. Create the VM

1. Sign up at [cloud.oracle.com](https://cloud.oracle.com) (free tier — a
   card is required for identity verification only, it is never charged
   unless you explicitly upgrade).
2. Create a compute instance:
   - Shape: **VM.Standard.A1.Flex** (Ampere ARM, Always Free eligible)
   - Resources: 4 OCPU / 24GB RAM (the max Always Free allows)
   - Image: **Ubuntu 22.04** (or latest LTS, ARM build)
   - Add your SSH key during creation
3. Under the instance's **Virtual Cloud Network > Security List**, add an
   ingress rule: TCP port **8000**, source `0.0.0.0/0` (or restrict to
   your IP if you don't need public access yet).

## 2. Install Docker on the VM

SSH in, then:

```bash
sudo apt update && sudo apt install -y docker.io docker-compose-v2
sudo usermod -aG docker $USER
newgrp docker
```

## 3. Deploy the app

```bash
git clone <your-repo-url> echoverse
cd echoverse
docker compose up -d --build
```

First run pulls the `ollama/ollama` image (~3GB) and builds the app image
— give it a few minutes. Then pull the model into the running container:

```bash
docker compose exec ollama ollama pull llama3.2:3b
```

## 4. Verify

```bash
curl http://localhost:8000/stats
curl -X POST http://localhost:8000/jobs \
  -H "Content-Type: application/json" \
  -d '{"text": "Hello from the cloud.", "tone": "neutral"}'
```

From your own machine: `http://<vm-public-ip>:8000/stats`

## 5. Notes for staying at $0

- Everything here (compute, storage, network egress within Oracle's free
  allowance) fits inside Always Free limits for a small personal project.
  Watch egress if you expect heavy public traffic — Always Free includes
  10TB/month outbound, which is generous for this use case.
- `docker-compose.yml`'s named volumes (`ollama_models`, `echoverse_data`)
  persist across container restarts/redeploys on the VM's disk — the
  SQLite DB and generated audio survive `docker compose down && up`.
- To update the app after a code change: `git pull && docker compose up -d --build`.

## 6. When you're ready to move off local models

Nothing here needs a rewrite. Per the original plan's swap path:

- **LLM**: point `OLLAMA_HOST` at a hosted inference API instead of the
  `ollama` service, or keep Ollama but move it to a GPU instance.
- **TTS**: swap `echoverse/agents/tts.py` for the ElevenLabs API (MCP
  server already scoped in the plan for this).
- **DB/storage**: swap SQLite (`echoverse/db.py`) for a Postgres
  connection string, and local `data/output/` for an S3/R2 client — the
  job contract (`create_job`/`update_job`/`get_job`) doesn't change.
