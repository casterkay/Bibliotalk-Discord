from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass
from datetime import UTC, datetime

from ..domain.models import Segment, Source, TranscriptLine, build_segment


def normalize_text(text: str) -> str:
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    text = text.lstrip("\ufeff")
    text = "\n".join(line.rstrip() for line in text.split("\n"))
    return text.strip()


def sha256_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


@dataclass(frozen=True, slots=True)
class ChunkingConfig:
    target_chars: int = 1200
    max_chars: int = 1500
    hard_max_chars: int = 1800


@dataclass(frozen=True, slots=True)
class _TranscriptMessage:
    text: str
    start_ms: int | None
    end_ms: int | None
    speaker: str | None


_PARA_SPLIT_RE = re.compile(r"\n\s*\n+")
_SENTENCE_END_RE = re.compile(r'[.!?\u3002\uFF01\uFF1F]["\')\]\u2019\u201D\uFF09\u3011]*$')


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


def _chunk_plain_text_default(source: Source, text: str, cfg: ChunkingConfig) -> list[Segment]:
    effective_max = min(cfg.max_chars, cfg.hard_max_chars)
    effective_target = min(cfg.target_chars, effective_max)

    paragraphs = [p.strip() for p in _PARA_SPLIT_RE.split(text) if p.strip()]
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
        for para_piece in _split_long(para, effective_max):
            piece_len = len(para_piece)
            if not buf:
                buf = [para_piece]
                buf_len = piece_len
                continue
            if buf_len + 2 + piece_len <= effective_max:
                buf.append(para_piece)
                buf_len += 2 + piece_len
            else:
                flush()
                buf = [para_piece]
                buf_len = piece_len

            if buf_len >= effective_target:
                flush()

    flush()
    segments: list[Segment] = []
    for seq, seg_text in enumerate(packed):
        if len(seg_text) > effective_max:
            raise ValueError(
                f"chunk_plain_text produced an oversized segment: {len(seg_text)} > {effective_max}"
            )
        segments.append(
            build_segment(
                source=source,
                seq=seq,
                text=seg_text.strip(),
                sha256=sha256_text(seg_text.strip()),
                start_ms=None,
                end_ms=None,
                speaker=None,
            )
        )
    return segments


def chunk_plain_text(
    source: Source, text: str, *, cfg: ChunkingConfig | None = None
) -> list[Segment]:
    cfg = cfg or ChunkingConfig()
    normalized = normalize_text(text)
    if not normalized:
        return []
    return _chunk_plain_text_default(source, normalized, cfg)


def _merge_transcript_messages(
    lines: list[TranscriptLine], cfg: ChunkingConfig
) -> list[_TranscriptMessage]:
    messages: list[_TranscriptMessage] = []
    cur_text_parts: list[str] = []
    cur_start: int | None = None
    cur_end: int | None = None
    cur_speaker: str | None = None

    def flush() -> None:
        nonlocal cur_text_parts, cur_start, cur_end, cur_speaker
        if not cur_text_parts:
            return
        merged = " ".join(part.strip() for part in cur_text_parts if part.strip()).strip()
        if merged:
            messages.append(
                _TranscriptMessage(
                    text=merged,
                    start_ms=cur_start,
                    end_ms=cur_end,
                    speaker=cur_speaker,
                )
            )
        cur_text_parts = []
        cur_start = None
        cur_end = None
        cur_speaker = None

    for line in lines:
        text = normalize_text(line.text)
        if not text:
            continue

        speaker_changed = cur_speaker is not None and line.speaker != cur_speaker
        has_large_gap = (
            cur_end is not None and line.start_ms is not None and (line.start_ms - cur_end) > 15_000
        )
        if cur_text_parts and (speaker_changed or has_large_gap):
            flush()

        if not cur_text_parts:
            cur_start = line.start_ms
            cur_speaker = line.speaker
        cur_end = line.end_ms
        cur_text_parts.append(text)

        if _SENTENCE_END_RE.search(text):
            flush()

    flush()
    return messages


def _resolve_published_at(source: Source) -> datetime | None:
    raw_meta = source.raw_meta or {}
    ts = raw_meta.get("timestamp")
    if isinstance(ts, (int, float)):
        try:
            return datetime.fromtimestamp(float(ts), tz=UTC)
        except (OSError, OverflowError, ValueError):
            pass
    if isinstance(ts, str) and ts.strip().isdigit():
        try:
            return datetime.fromtimestamp(float(ts.strip()), tz=UTC)
        except (OSError, OverflowError, ValueError):
            pass

    upload_date = raw_meta.get("upload_date")
    if isinstance(upload_date, str) and re.fullmatch(r"\d{8}", upload_date):
        try:
            return datetime.strptime(upload_date, "%Y%m%d").replace(tzinfo=UTC)
        except ValueError:
            pass

    if source.published_at:
        published = source.published_at
        if published.tzinfo is None:
            return published.replace(tzinfo=UTC)
        return published.astimezone(UTC)
    return None


def chunk_transcript(
    source: Source, lines: list[TranscriptLine], *, cfg: ChunkingConfig | None = None
) -> list[Segment]:
    cfg = cfg or ChunkingConfig(target_chars=1000, max_chars=1200)
    effective_max = min(cfg.max_chars, cfg.hard_max_chars)
    normalized_lines: list[TranscriptLine] = []
    for line in lines:
        text = normalize_text(line.text)
        if not text:
            continue
        normalized_lines.append(
            TranscriptLine(
                text=text,
                start_ms=line.start_ms,
                end_ms=line.end_ms,
                speaker=line.speaker,
            )
        )

    messages = _merge_transcript_messages(normalized_lines, cfg)
    published_at = _resolve_published_at(source)
    if source.published_at is None:
        source.published_at = published_at
    segments: list[Segment] = []
    for message in messages:
        if message.speaker:
            speaker_label = message.speaker.strip()
            if len(speaker_label) > 64:
                speaker_label = f"{speaker_label[:61]}..."
            prefix = f"{speaker_label}: "

            max_body = effective_max - len(prefix)
            if max_body < 50:
                # Speaker label is unexpectedly long; prefer preserving content over
                # producing segments that violate downstream hard limits.
                rendered_pieces = _split_long(message.text, effective_max)
            else:
                pieces = _split_long(message.text, max_body)
                rendered_pieces = [f"{prefix}{piece}" for piece in pieces]
        else:
            rendered_pieces = _split_long(message.text, effective_max)

        for piece in rendered_pieces:
            piece = piece.strip()
            if not piece:
                continue
            if len(piece) > effective_max:
                raise ValueError(
                    f"chunk_transcript produced an oversized segment: {len(piece)} > {effective_max}"
                )
            segments.append(
                build_segment(
                    source=source,
                    seq=len(segments),
                    text=piece,
                    sha256=sha256_text(piece),
                    start_ms=message.start_ms,
                    end_ms=message.end_ms,
                    speaker=message.speaker,
                )
            )
    return segments
