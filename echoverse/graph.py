"""Orchestrator: a LangGraph state machine wiring the EchoVerse agents
together with real closed loops (Milestone 2):

  Intake -> Rewrite+Critique (internal revision loop, up to 2 retries)
         -> TTS
         -> Audio-QA (re-transcribe + diff)
         -> [retry TTS once if QA fails] -> END

This replaces the flat, synchronous script from Milestone 1 with an
actual agentic graph: the Critic can send text back to the Rewriter,
and the Audio-QA agent can send audio back to the TTS agent, before
anything is considered "done".
"""

from __future__ import annotations

import os
import time
from pathlib import Path
from typing import TypedDict

from langgraph.graph import END, START, StateGraph

from echoverse.agents.audio_qa import qa_check
from echoverse.agents.intake import intake
from echoverse.agents.rewriter import rewrite_with_critique
from echoverse.agents.tts import synthesize_cast_segments_to_wav
from echoverse.agents.voice_casting import cast_segments

OUTPUT_DIR = Path(__file__).resolve().parent.parent / "data" / "output"
MAX_TTS_RETRIES = 1

# "piper" (default, local, free-forever) or "elevenlabs" (opt-in, free
# 10k-chars/month tier, real emotional prosody). Both support narrator/
# dialogue voice casting via the same Voice-Casting agent.
TTS_ENGINE = os.environ.get("TTS_ENGINE", "piper").lower()
if TTS_ENGINE not in ("piper", "elevenlabs"):
    print(f"[warn] Unknown TTS_ENGINE={TTS_ENGINE!r}, falling back to 'piper'")
    TTS_ENGINE = "piper"


class PipelineState(TypedDict):
    raw_text: str
    tone: str
    out_name: str
    chunks: list[str]
    rewritten: list[str]
    revision_log: list[dict]
    audio_path: str
    transcript: str
    qa_similarity: float
    qa_passed: bool
    tts_retries: int
    stage_seconds: dict
    total_revision_attempts: int
    chars_in: int
    chars_out: int


def node_intake(state: PipelineState) -> dict:
    t0 = time.perf_counter()
    chunks = intake(state["raw_text"], is_file=False)
    print(f"[intake] {len(chunks)} chunk(s)")
    stage_seconds = {**state["stage_seconds"], "intake": time.perf_counter() - t0}
    return {"chunks": [c.text for c in chunks], "stage_seconds": stage_seconds, "chars_in": len(state["raw_text"])}


def node_rewrite_and_critique(state: PipelineState) -> dict:
    t0 = time.perf_counter()
    rewritten: list[str] = []
    revision_log: list[dict] = []
    total_attempts = 0
    for i, chunk in enumerate(state["chunks"]):
        text, result, attempts = rewrite_with_critique(chunk, state["tone"])
        rewritten.append(text)
        total_attempts += attempts
        revision_log.append(
            {
                "chunk": i,
                "attempts": attempts,
                "approved": result.approved,
                "meaning_score": result.meaning_score,
                "tone_score": result.tone_score,
            }
        )
        status = "approved" if result.approved else "max-revisions-reached"
        print(f"[critic] chunk {i}: {status} after {attempts} revision(s) "
              f"(meaning={result.meaning_score}, tone={result.tone_score})")
    stage_seconds = {**state["stage_seconds"], "rewrite_and_critique": time.perf_counter() - t0}
    return {
        "rewritten": rewritten,
        "revision_log": revision_log,
        "stage_seconds": stage_seconds,
        "total_revision_attempts": total_attempts,
        "chars_out": sum(len(r) for r in rewritten),
    }


def node_tts(state: PipelineState) -> dict:
    t0 = time.perf_counter()
    out_path = OUTPUT_DIR / state["out_name"]
    full_text = " ".join(state["rewritten"])
    print(f"[tts] engine={TTS_ENGINE} synthesizing -> {out_path} (attempt {state.get('tts_retries', 0) + 1})")

    segments = cast_segments(full_text)
    voice_summary = ", ".join(sorted({s.role for s in segments}))
    print(f"[voice-casting] {len(segments)} segment(s) across roles: {voice_summary}")

    if TTS_ENGINE == "elevenlabs":
        from echoverse.agents.tts_elevenlabs import synthesize_cast_segments_to_wav as synthesize_elevenlabs

        synthesize_elevenlabs(segments, out_path, tone=state["tone"])
    else:
        synthesize_cast_segments_to_wav(segments, out_path)

    prior = state["stage_seconds"].get("tts", 0.0)
    stage_seconds = {**state["stage_seconds"], "tts": prior + (time.perf_counter() - t0)}
    return {"audio_path": str(out_path), "stage_seconds": stage_seconds}


def node_audio_qa(state: PipelineState) -> dict:
    t0 = time.perf_counter()
    expected = " ".join(state["rewritten"])
    result = qa_check(expected, state["audio_path"])
    print(f"[audio-qa] similarity={result.similarity:.2f} passed={result.passed}")
    prior = state["stage_seconds"].get("audio_qa", 0.0)
    stage_seconds = {**state["stage_seconds"], "audio_qa": prior + (time.perf_counter() - t0)}
    return {
        "transcript": result.transcript,
        "qa_similarity": result.similarity,
        "qa_passed": result.passed,
        "stage_seconds": stage_seconds,
    }


def route_after_qa(state: PipelineState) -> str:
    if state["qa_passed"]:
        return "done"
    if state.get("tts_retries", 0) < MAX_TTS_RETRIES:
        return "retry_tts"
    print("[audio-qa] QA failed after retries; shipping best-effort audio and flagging for review.")
    return "done"


def node_bump_retry(state: PipelineState) -> dict:
    return {"tts_retries": state.get("tts_retries", 0) + 1}


def build_graph():
    graph = StateGraph(PipelineState)
    graph.add_node("intake", node_intake)
    graph.add_node("rewrite_and_critique", node_rewrite_and_critique)
    graph.add_node("tts", node_tts)
    graph.add_node("audio_qa", node_audio_qa)
    graph.add_node("bump_retry", node_bump_retry)

    graph.add_edge(START, "intake")
    graph.add_edge("intake", "rewrite_and_critique")
    graph.add_edge("rewrite_and_critique", "tts")
    graph.add_edge("tts", "audio_qa")
    graph.add_conditional_edges(
        "audio_qa", route_after_qa, {"retry_tts": "bump_retry", "done": END}
    )
    graph.add_edge("bump_retry", "tts")

    return graph.compile()


def run(raw_text: str, tone: str = "neutral", out_name: str = "narration.wav") -> PipelineState:
    app = build_graph()
    t_start = time.perf_counter()
    initial: PipelineState = {
        "raw_text": raw_text,
        "tone": tone,
        "out_name": out_name,
        "chunks": [],
        "rewritten": [],
        "revision_log": [],
        "audio_path": "",
        "transcript": "",
        "qa_similarity": 0.0,
        "qa_passed": False,
        "tts_retries": 0,
        "stage_seconds": {},
        "total_revision_attempts": 0,
        "chars_in": 0,
        "chars_out": 0,
    }
    final_state = app.invoke(initial)
    final_state["stage_seconds"]["total"] = time.perf_counter() - t_start
    print(f"[done] {final_state['audio_path']} (qa_passed={final_state['qa_passed']})")
    print(f"[metrics] {final_state['stage_seconds']}")
    return final_state


if __name__ == "__main__":
    sample_text = (
        "The storm raged fiercely, lightning cracking across the sky as the "
        "ancient forest whispered secrets through the rustling leaves. "
        "A lone traveler pressed onward, unaware of what awaited beyond the treeline."
    )
    run(sample_text, tone="suspenseful")
