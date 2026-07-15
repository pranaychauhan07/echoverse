"""Voice-Casting agent: splits a rewritten passage into narration and
dialogue spans and tags each with a role, so a book with dialogue doesn't
get read in one flat voice front to back.

Engine-agnostic on purpose: this only decides *what* should be narrator
vs. dialogue, not *which* concrete voice that maps to. Each TTS backend
(echoverse/agents/tts.py for Piper, tts_elevenlabs.py for ElevenLabs)
owns its own role -> voice mapping, so both engines get the same casting
behavior without this module knowing about Piper .onnx paths or
ElevenLabs voice IDs.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Literal

Role = Literal["narrator", "dialogue"]

# Matches "double-quoted" or “curly-quoted” spans.
_QUOTE_SPAN = re.compile(r'["“][^"”]+["”]')


@dataclass
class VoiceSegment:
    role: Role
    text: str


def cast_segments(text: str) -> list[VoiceSegment]:
    """Split `text` into narration/dialogue segments, each tagged with
    the role that should read it."""
    segments: list[VoiceSegment] = []
    pos = 0
    for match in _QUOTE_SPAN.finditer(text):
        if match.start() > pos:
            narration = text[pos : match.start()].strip()
            if narration:
                segments.append(VoiceSegment("narrator", narration))
        dialogue = match.group().strip()
        if dialogue:
            segments.append(VoiceSegment("dialogue", dialogue))
        pos = match.end()

    remainder = text[pos:].strip()
    if remainder:
        segments.append(VoiceSegment("narrator", remainder))

    if not segments:
        segments.append(VoiceSegment("narrator", text))

    return segments
