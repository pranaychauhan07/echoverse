"""Async job worker: runs the LangGraph pipeline in a background thread
pool so the API can accept a job and return immediately instead of
blocking the request for the full rewrite -> critique -> TTS -> QA cycle.

This is the local, $0 stand-in for a real queue (Upstash Redis + Arq).
Swapping to a real queue later means replacing `submit_job`'s executor
call with an enqueue call -- the job contract (create_job/update_job in
db.py) does not change.
"""

from __future__ import annotations

import traceback
from concurrent.futures import ThreadPoolExecutor

from echoverse import db
from echoverse.graph import run as run_pipeline

# Kept small deliberately: this machine has 8GB RAM / a 4GB-VRAM GPU shared
# between Ollama and Whisper, so running many jobs concurrently would thrash
# rather than help.
_executor = ThreadPoolExecutor(max_workers=2)


def _execute(job_id: str, text: str, tone: str) -> None:
    db.update_job(job_id, status="running")
    try:
        out_name = f"{job_id}.wav"
        final_state = run_pipeline(text, tone=tone, out_name=out_name)
        metrics = {
            "stage_seconds": final_state["stage_seconds"],
            "chars_in": final_state["chars_in"],
            "chars_out": final_state["chars_out"],
            "revision_attempts": final_state["total_revision_attempts"],
            "tts_retries": final_state["tts_retries"],
        }
        db.update_job(
            job_id,
            status="done",
            rewritten_text=" ".join(final_state["rewritten"]),
            audio_path=final_state["audio_path"],
            transcript=final_state["transcript"],
            qa_similarity=final_state["qa_similarity"],
            qa_passed=final_state["qa_passed"],
            revision_log=final_state["revision_log"],
            metrics=metrics,
        )
    except Exception:
        db.update_job(job_id, status="failed", error=traceback.format_exc())


def submit_job(text: str, tone: str) -> str:
    job_id = db.create_job(source_text=text, tone=tone)
    _executor.submit(_execute, job_id, text, tone)
    return job_id
