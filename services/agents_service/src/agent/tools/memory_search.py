"""Memory search tool: EMOS retrieve + local rerank + Evidence mapping."""

from __future__ import annotations

from typing import Any, Awaitable, Callable

from bt_common.citation import Evidence
from bt_common.segment import Segment, bm25_rerank

SegmentsProvider = Callable[[str], Awaitable[list[dict[str, Any]]]]


def _extract_query_terms(search_payload: dict[str, Any]) -> list[str]:
    result = search_payload.get("result", {})
    memories = result.get("memories", [])
    terms: list[str] = []
    for memory_group in memories:
        for entries in memory_group.values():
            for item in entries:
                summary = item.get("summary")
                if summary:
                    terms.append(summary)
    return terms


class MemorySearchTool:
    def __init__(
        self,
        *,
        evermemos_client: Any,
        segments_provider: SegmentsProvider,
        top_k: int = 8,
    ):
        self.evermemos_client = evermemos_client
        self.segments_provider = segments_provider
        self.top_k = top_k

    async def __call__(self, query: str, agent_id: str) -> list[Evidence]:
        search_result = await self.evermemos_client.search(
            query,
            user_id=agent_id,
            retrieve_method="rrf",
            top_k=self.top_k,
        )

        segment_rows = await self.segments_provider(agent_id)
        if not segment_rows:
            return []

        segments = [Segment.model_validate(row) for row in segment_rows]
        query_terms = " ".join(_extract_query_terms(search_result))
        ranking_query = query_terms or query
        reranked = bm25_rerank(ranking_query, segments, top_k=self.top_k)

        row_by_segment_id: dict[str, dict[str, Any]] = {}
        row_by_emos_message_id: dict[str, dict[str, Any]] = {}
        for row in segment_rows:
            segment_id = row.get("id")
            if segment_id is not None:
                row_by_segment_id[str(segment_id)] = row
            emos_message_id = row.get("emos_message_id")
            if emos_message_id is not None:
                row_by_emos_message_id[str(emos_message_id)] = row

        evidences: list[Evidence] = []
        for segment in reranked:
            row = (
                row_by_segment_id.get(str(segment.id))
                or row_by_emos_message_id.get(str(segment.emos_message_id))
                or {}
            )
            source_title = row.get("source_title", "Unknown Source")
            source_url = row.get("source_url", "")
            evidences.append(
                Evidence(
                    segment_id=segment.id,
                    emos_message_id=segment.emos_message_id,
                    source_title=source_title,
                    source_url=source_url,
                    text=segment.text,
                    platform=segment.platform,
                )
            )
        return evidences