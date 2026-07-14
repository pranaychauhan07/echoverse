"""Audio-QA agent: re-transcribes synthesized narration with a local
Whisper model and diffs it against the script that was supposed to be
spoken, to catch TTS mispronunciations, dropped words, or garbled audio.

This closes the loop on the audio side the same way the Critic agent
closes it on the text side.
"""

from __future__ import annotations

import difflib
import re
from dataclasses import dataclass
from pathlib import Path

from faster_whisper import WhisperModel

DEFAULT_WHISPER_MODEL = "tiny.en"
SIMILARITY_THRESHOLD = 0.75

_model_cache: dict[str, WhisperModel] = {}


def _get_model(model_size: str = DEFAULT_WHISPER_MODEL) -> WhisperModel:
    if model_size not in _model_cache:
        _model_cache[model_size] = WhisperModel(model_size, device="cpu", compute_type="int8")
    return _model_cache[model_size]


@dataclass
class AudioQAResult:
    transcript: str
    similarity: float

    @property
    def passed(self) -> bool:
        return self.similarity >= SIMILARITY_THRESHOLD


def transcribe(wav_path: str | Path, model_size: str = DEFAULT_WHISPER_MODEL) -> str:
    model = _get_model(model_size)
    segments, _info = model.transcribe(str(wav_path))
    return " ".join(segment.text.strip() for segment in segments).strip()


def _normalize(s: str) -> str:
    s = s.lower()
    s = re.sub(r"[^a-z0-9\s]", "", s)  # strip punctuation/apostrophes/hyphens
    return " ".join(s.split())


def _similarity(expected: str, actual: str) -> float:
    return difflib.SequenceMatcher(None, _normalize(expected), _normalize(actual)).ratio()


def qa_check(expected_text: str, wav_path: str | Path, model_size: str = DEFAULT_WHISPER_MODEL) -> AudioQAResult:
    transcript = transcribe(wav_path, model_size=model_size)
    score = _similarity(expected_text, transcript)
    return AudioQAResult(transcript=transcript, similarity=score)
