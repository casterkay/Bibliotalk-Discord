"""Emit and validate citations from evidence objects."""

from __future__ import annotations

import contextvars
from typing import Any, Awaitable, Callable
from uuid import UUID

from ...models.citation import Citation, Evidence, SegmentLike, validate_citations

SegmentsByIdsProvider = Callable[[list[UUID]], Awaitable[list[dict[str, Any]]]]

_last_citations: contextvars.ContextVar[list[Citation]] = contextvars.ContextVar("last_citations", default=[])


class EmitCitationsTool:
    def __init__(self, *, segments_by_ids_provider: SegmentsByIdsProvider):
        self.segments_by_ids_provider = segments_by_ids_provider

    async def __call__(self, evidence_items: list[Evidence], agent_id: str) -> list[Citation]:
        if not evidence_items:
            _last_citations.set([])
            return []

        citations: list[Citation] = []
        for idx, evidence in enumerate(evidence_items, start=1):
            quote = evidence.text[:160].strip()
            citations.append(Citation.from_evidence(evidence, index=idx, quote=quote))

        rows = await self.segments_by_ids_provider([item.segment_id for item in evidence_items])
        segments = [
            SegmentLike(
                id=row["id"],
                agent_id=row["agent_id"],
                text=row["text"],
            )
            for row in rows
        ]

        valid = validate_citations(citations, segments, responding_agent_id=UUID(agent_id))
        _last_citations.set(valid)
        return valid


def get_last_citations() -> list[Citation]:
    return _last_citations.get()
