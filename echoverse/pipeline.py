"""Milestone 1: synchronous Intake -> Rewriter -> TTS pipeline.
No critic loop, no async job queue yet -- just proving the core flow works.
"""

from __future__ import annotations

from pathlib import Path

from echoverse.agents.intake import intake
from echoverse.agents.rewriter import rewrite_chunks
from echoverse.agents.tts import synthesize_chunks_to_wav

OUTPUT_DIR = Path(__file__).resolve().parent.parent / "data" / "output"


def run_pipeline(text: str, tone: str = "neutral", out_name: str = "narration.wav") -> Path:
    print(f"[intake] chunking input ({len(text)} chars)...")
    chunks = intake(text, is_file=False)
    print(f"[intake] {len(chunks)} chunk(s)")

    print(f"[rewriter] rewriting in '{tone}' tone using llama3.2:3b...")
    rewritten = rewrite_chunks([c.text for c in chunks], tone=tone)
    for i, r in enumerate(rewritten):
        print(f"  chunk {i}: {r[:80]}...")

    out_path = OUTPUT_DIR / out_name
    print(f"[tts] synthesizing audio to {out_path}...")
    synthesize_chunks_to_wav(rewritten, out_path)

    print(f"[done] wrote {out_path}")
    return out_path


if __name__ == "__main__":
    sample_text = (
        "The storm raged fiercely, lightning cracking across the sky as the "
        "ancient forest whispered secrets through the rustling leaves. "
        "A lone traveler pressed onward, unaware of what awaited beyond the treeline."
    )
    run_pipeline(sample_text, tone="suspenseful")
