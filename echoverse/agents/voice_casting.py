"""Voice-Casting agent: splits a rewritten passage into narration and
dialogue spans and assigns a distinct local voice to each, so a book
with dialogue doesn't get read in one flat voice front to back.

This is a real, $0-cost differentiator (regex-based speaker attribution +
two local Piper voices) -- true per-character voice casting is a later,
larger upgrade, but narrator-vs-dialogue is genuinely useful today.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path

VOICES_DIR = Path(__file__).resolve().parent.parent.parent / "voices"

NARRATOR_VOICE = VOICES_DIR / "en_US-lessac-medium.onnx"
DIALOGUE_VOICE = VOICES_DIR / "en_US-amy-medium.onnx"

# Matches "double-quoted" or “curly-quoted” spans.
_QUOTE_SPAN = re.compile(r'["“][^"”]+["”]')


@dataclass
class VoiceSegment:
    voice_path: Path
    text: str


def cast_segments(text: str) -> list[VoiceSegment]:
    """Split `text` into narration/dialogue segments, each tagged with
    the voice that should read it."""
    segments: list[VoiceSegment] = []
    pos = 0
    for match in _QUOTE_SPAN.finditer(text):
        if match.start() > pos:
            narration = text[pos : match.start()].strip()
            if narration:
                segments.append(VoiceSegment(NARRATOR_VOICE, narration))
        dialogue = match.group().strip()
        if dialogue:
            segments.append(VoiceSegment(DIALOGUE_VOICE, dialogue))
        pos = match.end()

    remainder = text[pos:].strip()
    if remainder:
        segments.append(VoiceSegment(NARRATOR_VOICE, remainder))

    if not segments:
        segments.append(VoiceSegment(NARRATOR_VOICE, text))

    return segments
