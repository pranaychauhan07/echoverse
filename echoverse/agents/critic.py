"""Critic agent: scores a rewritten passage against the original for
meaning-preservation, tone-fidelity, and safety. Sends structured feedback
back to the Rewriter agent when a passage doesn't clear the bar.

This closed loop (Rewriter <-> Critic) is what makes the text stage
"agentic" rather than a one-shot generate_text() call.
"""

from __future__ import annotations

import json
from dataclasses import dataclass

import ollama

DEFAULT_MODEL = "llama3.2:3b"

MEANING_THRESHOLD = 7
TONE_THRESHOLD = 6

SYSTEM_PROMPT = (
    "You are a strict quality reviewer for an audiobook rewriting pipeline. "
    "Given an ORIGINAL passage and a REWRITTEN passage that was supposed to be "
    "restyled into a target TONE, evaluate the rewrite. "
    "Respond with ONLY a JSON object, no other text, matching this schema:\n"
    '{"meaning_score": <0-10 integer, how well facts/events/characters are preserved>, '
    '"tone_score": <0-10 integer, how well the target tone was achieved>, '
    '"safety_ok": <true/false, false only if content is harmful/inappropriate>, '
    '"feedback": <short string, concrete instruction for improving the rewrite if scores are low, '
    'or "" if no issues>}'
)


@dataclass
class CritiqueResult:
    meaning_score: int
    tone_score: int
    safety_ok: bool
    feedback: str

    @property
    def approved(self) -> bool:
        return (
            self.meaning_score >= MEANING_THRESHOLD
            and self.tone_score >= TONE_THRESHOLD
            and self.safety_ok
        )


def critique(original: str, rewritten: str, tone: str, model: str = DEFAULT_MODEL) -> CritiqueResult:
    prompt = (
        f"TARGET TONE: {tone}\n\n"
        f"ORIGINAL:\n\"\"\"\n{original}\n\"\"\"\n\n"
        f"REWRITTEN:\n\"\"\"\n{rewritten}\n\"\"\""
    )

    response = ollama.chat(
        model=model,
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": prompt},
        ],
        format="json",
        options={"temperature": 0.0},
    )

    raw = response["message"]["content"].strip()
    try:
        data = json.loads(raw)
        return CritiqueResult(
            meaning_score=int(data.get("meaning_score", 0)),
            tone_score=int(data.get("tone_score", 0)),
            safety_ok=bool(data.get("safety_ok", True)),
            feedback=str(data.get("feedback", "")),
        )
    except (json.JSONDecodeError, ValueError, TypeError):
        # If the critic itself fails to produce valid JSON, fail open with a
        # low score so the orchestrator flags it for revision rather than
        # silently shipping unverified output.
        return CritiqueResult(meaning_score=0, tone_score=0, safety_ok=True, feedback="Critic returned unparseable output; retry.")
