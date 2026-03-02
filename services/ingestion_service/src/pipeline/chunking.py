from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass

from ..domain.models import Segment, Source, TranscriptLine, build_segment


def normalize_text(text: str) -> str:
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    text = text.lstrip("\ufeff")
    # Strip trailing whitespace deterministically per line.
    text = "\n".join(line.rstrip() for line in text.split("\n"))
    return text.strip()


def sha256_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


@dataclass(frozen=True, slots=True)
class ChunkingConfig:
    target_chars: int = 1200
    max_chars: int = 1500


_PARA_SPLIT_RE = re.compile(r"\n\s*\n+")


def _split_long(text: str, max_chars: int) -> list[str]:
    text = text.strip()
    if len(text) <= max_chars:
        return [text]

    parts: list[str] = []
    remaining = text
    while remaining:
        if len(remaining) <= max_chars:
            parts.append(remaining.strip())
            break
        cut = remaining.rfind(" ", 0, max_chars + 1)
        if cut < max_chars * 0.6:
            cut = max_chars
        parts.append(remaining[:cut].strip())
        remaining = remaining[cut:].strip()
    return [p for p in parts if p]


def chunk_plain_text(source: Source, text: str, *, cfg: ChunkingConfig | None = None) -> list[Segment]:
    cfg = cfg or ChunkingConfig()
    normalized = normalize_text(text)
    if not normalized:
        return []

    paragraphs = [p.strip() for p in _PARA_SPLIT_RE.split(normalized) if p.strip()]
    packed: list[str] = []
    buf: list[str] = []
    buf_len = 0

    def flush() -> None:
        nonlocal buf, buf_len
        if not buf:
            return
        packed.append("\n\n".join(buf).strip())
        buf = []
        buf_len = 0

    for para in paragraphs:
        for para_piece in _split_long(para, cfg.max_chars):
            piece_len = len(para_piece)
            if not buf:
                buf = [para_piece]
                buf_len = piece_len
                continue
            # +2 for paragraph separator
            if buf_len + 2 + piece_len <= cfg.max_chars:
                buf.append(para_piece)
                buf_len += 2 + piece_len
            else:
                flush()
                buf = [para_piece]
                buf_len = piece_len

            if buf_len >= cfg.target_chars:
                flush()

    flush()

    segments: list[Segment] = []
    for seq, seg_text in enumerate(packed):
        seg_text = seg_text.strip()
        segments.append(build_segment(source=source, seq=seq, text=seg_text, sha256=sha256_text(seg_text), start_ms=None, end_ms=None, speaker=None))
    return segments


def _format_ts(ms: int) -> str:
    seconds = max(0, ms) // 1000
    h, rem = divmod(seconds, 3600)
    m, s = divmod(rem, 60)
    if h:
        return f"{h:02d}:{m:02d}:{s:02d}"
    return f"{m:02d}:{s:02d}"


def chunk_transcript(source: Source, lines: list[TranscriptLine], *, cfg: ChunkingConfig | None = None) -> list[Segment]:
    cfg = cfg or ChunkingConfig(target_chars=1000, max_chars=1200)
    normalized_lines: list[TranscriptLine] = []
    for line in lines:
        text = normalize_text(line.text)
        if not text:
            continue
        normalized_lines.append(TranscriptLine(text=text, start_ms=line.start_ms, end_ms=line.end_ms, speaker=line.speaker))

    segments: list[Segment] = []
    buf: list[str] = []
    buf_len = 0
    seg_start: int | None = None
    seg_end: int | None = None
    seg_speaker: str | None = None

    def flush() -> None:
        nonlocal buf, buf_len, seg_start, seg_end, seg_speaker
        if not buf:
            return
        seg_text = "\n".join(buf).strip()
        segments.append(
            build_segment(
                source=source,
                seq=len(segments),
                text=seg_text,
                sha256=sha256_text(seg_text),
                start_ms=seg_start,
                end_ms=seg_end,
                speaker=seg_speaker,
            )
        )
        buf = []
        buf_len = 0
        seg_start = None
        seg_end = None
        seg_speaker = None

    for line in normalized_lines:
        prefix = ""
        if line.start_ms is not None:
            prefix = f"[{_format_ts(line.start_ms)}] "
        speaker = f"{line.speaker}: " if line.speaker else ""
        rendered = f"{prefix}{speaker}{line.text}".strip()
        rendered_len = len(rendered)
        if not buf:
            buf = [rendered]
            buf_len = rendered_len
            seg_start = line.start_ms
            seg_end = line.end_ms
            seg_speaker = line.speaker
        else:
            if buf_len + 1 + rendered_len <= cfg.max_chars:
                buf.append(rendered)
                buf_len += 1 + rendered_len
                seg_end = line.end_ms
            else:
                flush()
                buf = [rendered]
                buf_len = rendered_len
                seg_start = line.start_ms
                seg_end = line.end_ms
                seg_speaker = line.speaker

        if buf_len >= cfg.target_chars:
            flush()

    flush()
    return segments
