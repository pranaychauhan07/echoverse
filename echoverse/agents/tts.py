"""TTS Synthesis agent: turns rewritten text chunks into narrated audio
using a local Piper voice model (self-hosted, $0, CPU-friendly)."""

from __future__ import annotations

import wave
from pathlib import Path

from piper import PiperVoice

VOICES_DIR = Path(__file__).resolve().parent.parent.parent / "voices"
DEFAULT_VOICE_MODEL = VOICES_DIR / "en_US-lessac-medium.onnx"

_voice_cache: dict[str, PiperVoice] = {}


def _get_voice(model_path: Path = DEFAULT_VOICE_MODEL) -> PiperVoice:
    key = str(model_path)
    if key not in _voice_cache:
        _voice_cache[key] = PiperVoice.load(str(model_path))
    return _voice_cache[key]


def synthesize_to_wav(text: str, out_path: str | Path, model_path: Path = DEFAULT_VOICE_MODEL) -> Path:
    """Synthesize `text` to a .wav file at `out_path`."""
    voice = _get_voice(model_path)
    out_path = Path(out_path)
    out_path.parent.mkdir(parents=True, exist_ok=True)

    with wave.open(str(out_path), "wb") as wav_file:
        voice.synthesize_wav(text, wav_file)

    return out_path


def synthesize_chunks_to_wav(texts: list[str], out_path: str | Path, model_path: Path = DEFAULT_VOICE_MODEL) -> Path:
    """Synthesize multiple chunks and concatenate them into a single .wav file."""
    voice = _get_voice(model_path)
    out_path = Path(out_path)
    out_path.parent.mkdir(parents=True, exist_ok=True)

    with wave.open(str(out_path), "wb") as wav_file:
        for i, text in enumerate(texts):
            voice.synthesize_wav(text, wav_file, set_wav_format=(i == 0))

    return out_path


def synthesize_cast_segments_to_wav(segments: list, out_path: str | Path) -> Path:
    """Synthesize a list of `VoiceSegment` (voice_path, text) into a single
    stitched .wav, switching voices per segment. All bundled Piper voices
    are 22050Hz mono, so segments concatenate cleanly into one WAV format."""
    out_path = Path(out_path)
    out_path.parent.mkdir(parents=True, exist_ok=True)

    with wave.open(str(out_path), "wb") as wav_file:
        for i, seg in enumerate(segments):
            voice = _get_voice(seg.voice_path)
            voice.synthesize_wav(seg.text, wav_file, set_wav_format=(i == 0))

    return out_path
