"""Intake agent: reads raw text/.txt/.pdf input, cleans it, and chunks it
into LLM- and TTS-friendly pieces that respect sentence boundaries."""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path

from pypdf import PdfReader

_SENTENCE_SPLIT = re.compile(r"(?<=[.!?])\s+")


@dataclass
class TextChunk:
    index: int
    text: str


def load_text(path: str | Path) -> str:
    """Read plain text from a .txt or .pdf file."""
    path = Path(path)
    if path.suffix.lower() == ".pdf":
        reader = PdfReader(str(path))
        return "\n".join(page.extract_text() or "" for page in reader.pages)
    return path.read_text(encoding="utf-8", errors="ignore")


def clean_text(raw: str) -> str:
    """Collapse whitespace/newlines without destroying paragraph breaks."""
    normalized = raw.replace("\r\n", "\n").replace("\r", "\n")
    normalized = re.sub(r"[ \t]+", " ", normalized)
    normalized = re.sub(r"\n{3,}", "\n\n", normalized)
    return normalized.strip()


def chunk_text(text: str, max_chars: int = 800) -> list[TextChunk]:
    """Split text into chunks under `max_chars`, breaking on sentence
    boundaries so the LLM and TTS never see a sentence cut in half."""
    sentences = _SENTENCE_SPLIT.split(text.replace("\n", " "))

    chunks: list[str] = []
    current = ""
    for sentence in sentences:
        sentence = sentence.strip()
        if not sentence:
            continue
        candidate = f"{current} {sentence}".strip() if current else sentence
        if len(candidate) > max_chars and current:
            chunks.append(current)
            current = sentence
        else:
            current = candidate
    if current:
        chunks.append(current)

    return [TextChunk(index=i, text=c) for i, c in enumerate(chunks)]


def intake(path_or_text: str, is_file: bool = False, max_chars: int = 800) -> list[TextChunk]:
    raw = load_text(path_or_text) if is_file else path_or_text
    return chunk_text(clean_text(raw), max_chars=max_chars)
