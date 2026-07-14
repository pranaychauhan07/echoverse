"""Tone Rewriter agent: rewrites text chunks in a target tone using a
local Ollama model. Prompt-chained (system instructions + per-chunk call)
to preserve meaning while shifting style."""

from __future__ import annotations

import ollama

DEFAULT_MODEL = "llama3.2:3b"

TONE_INSTRUCTIONS = {
    "neutral": "Rewrite the text in a clear, neutral, informative tone. Keep it natural to read aloud.",
    "suspenseful": "Rewrite the text in a suspenseful, dramatic tone that builds tension, while keeping every fact and event the same.",
    "inspiring": "Rewrite the text in an inspiring, motivational tone that energizes the listener, while keeping every fact and event the same.",
}

SYSTEM_PROMPT = (
    "You are a professional audiobook editor. You rewrite passages in a requested "
    "tone WITHOUT changing their meaning, facts, characters, or events. "
    "Output ONLY the rewritten passage — no preamble, no notes, no quotation marks."
)


def rewrite_chunk(text: str, tone: str, model: str = DEFAULT_MODEL, feedback: str | None = None) -> str:
    tone_key = tone.lower().strip()
    if tone_key not in TONE_INSTRUCTIONS:
        raise ValueError(f"Unknown tone '{tone}'. Choose from: {list(TONE_INSTRUCTIONS)}")

    prompt = f"{TONE_INSTRUCTIONS[tone_key]}\n\nOriginal passage:\n\"\"\"\n{text}\n\"\"\""
    if feedback:
        prompt += f"\n\nA reviewer flagged your previous attempt with this feedback — address it: {feedback}"

    response = ollama.chat(
        model=model,
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": prompt},
        ],
        options={"temperature": 0.5},
    )
    return response["message"]["content"].strip()


def rewrite_chunks(chunks: list[str], tone: str, model: str = DEFAULT_MODEL) -> list[str]:
    return [rewrite_chunk(c, tone, model=model) for c in chunks]


def rewrite_with_critique(text: str, tone: str, model: str = DEFAULT_MODEL, max_revisions: int = 2):
    """Rewrite a chunk, then loop it through the Critic agent, revising up
    to `max_revisions` times until the critique is approved or attempts run out."""
    from echoverse.agents.critic import critique  # local import avoids a hard cycle at module load

    rewritten = rewrite_chunk(text, tone, model=model)
    result = critique(text, rewritten, tone, model=model)

    attempts = 0
    while not result.approved and attempts < max_revisions:
        attempts += 1
        rewritten = rewrite_chunk(text, tone, model=model, feedback=result.feedback)
        result = critique(text, rewritten, tone, model=model)

    return rewritten, result, attempts
