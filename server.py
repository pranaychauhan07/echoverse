"""EchoVerse API: submit narration jobs, poll status, fetch audio, browse
persistent history. Run with:

    uv run uvicorn server:app --reload
"""

from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi import FastAPI, File, HTTPException, UploadFile
from fastapi.responses import FileResponse
from pydantic import BaseModel

from echoverse import db
from echoverse.agents.intake import clean_text
from echoverse.worker import submit_job

VALID_TONES = {"neutral", "suspenseful", "inspiring"}


@asynccontextmanager
async def lifespan(_app: FastAPI):
    db.init_db()
    yield


app = FastAPI(title="EchoVerse", lifespan=lifespan)


class JobRequest(BaseModel):
    text: str
    tone: str = "neutral"


class JobResponse(BaseModel):
    job_id: str
    status: str


def _validate_tone(tone: str) -> str:
    tone = tone.lower().strip()
    if tone not in VALID_TONES:
        raise HTTPException(400, f"tone must be one of {sorted(VALID_TONES)}")
    return tone


@app.post("/jobs", response_model=JobResponse)
def create_job(req: JobRequest) -> JobResponse:
    tone = _validate_tone(req.tone)
    if not req.text.strip():
        raise HTTPException(400, "text must not be empty")
    job_id = submit_job(req.text, tone)
    return JobResponse(job_id=job_id, status="queued")


@app.post("/jobs/upload", response_model=JobResponse)
async def create_job_from_file(tone: str = "neutral", file: UploadFile = File(...)) -> JobResponse:
    tone = _validate_tone(tone)
    raw = (await file.read()).decode("utf-8", errors="ignore")
    text = clean_text(raw)
    if not text:
        raise HTTPException(400, "uploaded file had no readable text")
    job_id = submit_job(text, tone)
    return JobResponse(job_id=job_id, status="queued")


@app.get("/jobs")
def list_jobs(limit: int = 50) -> list[dict]:
    return db.list_jobs(limit=limit)


@app.get("/stats")
def get_stats() -> dict:
    """Usage/latency dashboard. Everything is $0 today (local LLM + local
    TTS + local Whisper), but tracking real chars/seconds-per-job now means
    the moment a paid swap (ElevenLabs, hosted inference) is flipped on,
    actual usage volume is already known instead of guessed."""
    return db.get_stats()


@app.get("/jobs/{job_id}")
def get_job(job_id: str) -> dict:
    job = db.get_job(job_id)
    if not job:
        raise HTTPException(404, "job not found")
    return job


@app.get("/jobs/{job_id}/audio")
def get_job_audio(job_id: str) -> FileResponse:
    job = db.get_job(job_id)
    if not job:
        raise HTTPException(404, "job not found")
    if job["status"] != "done" or not job["audio_path"]:
        raise HTTPException(409, f"job is not done yet (status={job['status']})")
    return FileResponse(job["audio_path"], media_type="audio/wav")
