"""ElevenLabs TTS backend -- the paid-tier-quality swap-in flagged
throughout the plan, usable today within the free 10k-credits/month tier.

Feature-matches the Piper backend: narrator/dialogue voice casting (via
the same engine-agnostic Voice-Casting agent) and tone-aware delivery --
though here "tone-aware" means real prosody control (ElevenLabs
`voice_settings`), not just a different voice file.
"""

from __future__ import annotations

import io
import os
import wave
from pathlib import Path

from elevenlabs.client import ElevenLabs
from elevenlabs.core.api_error import ApiError
from elevenlabs.types import VoiceSettings

DEFAULT_MODEL_ID = "eleven_multilingual_v2"

# Free-tier accounts can only use voices in their own account (the ~20
# default premade voices every account gets), not the shared community
# voice library -- using a library voice returns 402 payment_required.
# "George" / "Sarah" are two of those defaults, picked for a clear
# narrator/dialogue contrast; override via env if you'd rather use others.
ROLE_VOICE_IDS = {
    "narrator": os.environ.get("ELEVENLABS_NARRATOR_VOICE_ID", "JBFqnCBsd6RMkjVDRZzb"),  # George
    "dialogue": os.environ.get("ELEVENLABS_DIALOGUE_VOICE_ID", "EXAVITQu4vr4xnSDxMaL"),  # Sarah
}
DEFAULT_VOICE_ID = os.environ.get("ELEVENLABS_VOICE_ID", ROLE_VOICE_IDS["narrator"])

# stability: lower = more expressive/variable delivery, higher = flatter and
# more consistent. style: how much the model exaggerates the voice's
# inherent character. Tuned per tone rather than left at API defaults.
TONE_VOICE_SETTINGS = {
    "neutral": VoiceSettings(stability=0.7, similarity_boost=0.75, style=0.0, use_speaker_boost=True),
    "suspenseful": VoiceSettings(stability=0.35, similarity_boost=0.75, style=0.6, use_speaker_boost=True),
    "inspiring": VoiceSettings(stability=0.45, similarity_boost=0.8, style=0.45, use_speaker_boost=True),
}
DEFAULT_VOICE_SETTINGS = TONE_VOICE_SETTINGS["neutral"]

_client: ElevenLabs | None = None


class ElevenLabsError(RuntimeError):
    """Wraps ApiError with a message clear enough to show a user directly
    (missing key, exhausted quota, invalid voice, etc.) instead of a raw
    SDK traceback."""


def _get_client() -> ElevenLabs:
    global _client
    if _client is None:
        api_key = os.environ.get("ELEVENLABS_API_KEY")
        if not api_key:
            raise ElevenLabsError(
                "ELEVENLABS_API_KEY is not set. Set TTS_ENGINE=piper to use the "
                "free local engine instead, or set ELEVENLABS_API_KEY to use ElevenLabs."
            )
        _client = ElevenLabs(api_key=api_key)
    return _client


def _synthesize_segment(
    client: ElevenLabs,
    text: str,
    voice_id: str,
    voice_settings: VoiceSettings,
    model_id: str,
    previous_text: str | None = None,
    next_text: str | None = None,
) -> bytes:
    try:
        chunks = client.text_to_speech.convert(
            voice_id=voice_id,
            text=text,
            model_id=model_id,
            output_format="wav_22050",
            voice_settings=voice_settings,
            previous_text=previous_text,
            next_text=next_text,
        )
        return b"".join(chunks)
    except ApiError as e:
        detail = (e.body or {}).get("detail", {}) if isinstance(e.body, dict) else {}
        code = detail.get("code", "")
        message = detail.get("message", str(e))
        if e.status_code == 401 and "quota" in message.lower():
            raise ElevenLabsError(f"ElevenLabs free-tier quota exhausted: {message}") from e
        if e.status_code == 402:
            raise ElevenLabsError(
                f"ElevenLabs voice '{voice_id}' isn't usable on this plan: {message}. "
                "Free tier can only use voices already in your account, not the shared library."
            ) from e
        raise ElevenLabsError(f"ElevenLabs API error ({code or e.status_code}): {message}") from e


def synthesize_to_wav(
    text: str,
    out_path: str | Path,
    voice_id: str = DEFAULT_VOICE_ID,
    tone: str = "neutral",
    model_id: str = DEFAULT_MODEL_ID,
) -> Path:
    """Synthesize the whole passage in a single call -- best prosody for
    plain narration with no dialogue to cast."""
    out_path = Path(out_path)
    out_path.parent.mkdir(parents=True, exist_ok=True)

    client = _get_client()
    settings = TONE_VOICE_SETTINGS.get(tone, DEFAULT_VOICE_SETTINGS)
    audio_bytes = _synthesize_segment(client, text, voice_id, settings, model_id)

    with open(out_path, "wb") as f:
        f.write(audio_bytes)

    return out_path


def synthesize_cast_segments_to_wav(
    segments: list,
    out_path: str | Path,
    tone: str = "neutral",
    model_id: str = DEFAULT_MODEL_ID,
) -> Path:
    """Synthesize a list of `VoiceSegment` (role, text), switching voices
    per segment role, and stitch into one .wav. Each segment is passed its
    neighbors' text as ElevenLabs `previous_text`/`next_text` context so
    the voice switches don't lose pacing across the boundary."""
    out_path = Path(out_path)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    client = _get_client()
    settings = TONE_VOICE_SETTINGS.get(tone, DEFAULT_VOICE_SETTINGS)

    with wave.open(str(out_path), "wb") as out_wav:
        for i, seg in enumerate(segments):
            voice_id = ROLE_VOICE_IDS.get(seg.role, DEFAULT_VOICE_ID)
            previous_text = segments[i - 1].text if i > 0 else None
            next_text = segments[i + 1].text if i + 1 < len(segments) else None

            audio_bytes = _synthesize_segment(
                client, seg.text, voice_id, settings, model_id, previous_text, next_text
            )

            with wave.open(io.BytesIO(audio_bytes), "rb") as seg_wav:
                if i == 0:
                    out_wav.setframerate(seg_wav.getframerate())
                    out_wav.setsampwidth(seg_wav.getsampwidth())
                    out_wav.setnchannels(seg_wav.getnchannels())
                out_wav.writeframes(seg_wav.readframes(seg_wav.getnframes()))

    return out_path
