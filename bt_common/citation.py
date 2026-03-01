"""Citation and evidence models with validation helpers."""

from __future__ import annotations

from datetime import datetime
from typing import Iterable, Sequence
from uuid import UUID

from pydantic import BaseModel, Field


class Evidence(BaseModel):
    segment_id: UUID
    emos_message_id: str
    source_title: str
    source_url: str
    text: str
    platform: str


class Citation(BaseModel):
    index: int = Field(ge=1)
    segment_id: UUID
    emos_message_id: str
    source_title: str
    source_url: str
    quote: str = Field(min_length=1)
    platform: str
    timestamp: datetime | None = None

    @classmethod
    def from_evidence(cls, evidence: Evidence, *, index: int, quote: str) -> "Citation":
        return cls(
            index=index,
            segment_id=evidence.segment_id,
            emos_message_id=evidence.emos_message_id,
            source_title=evidence.source_title,
            source_url=evidence.source_url,
            quote=quote,
            platform=evidence.platform,
        )


class SegmentLike(BaseModel):
    id: UUID
    agent_id: UUID
    text: str


def validate_citations(
    citations: Iterable[Citation],
    segments: Sequence[SegmentLike],
    *,
    responding_agent_id: UUID,
) -> list[Citation]:
    """Keep only citations whose segment exists, belongs to agent, and contains quote."""

    segments_by_id = {segment.id: segment for segment in segments}
    valid: list[Citation] = []

    for citation in citations:
        segment = segments_by_id.get(citation.segment_id)
        if segment is None:
            continue
        if segment.agent_id != responding_agent_id:
            continue
        if citation.quote not in segment.text:
            continue
        valid.append(citation)

    return valid
