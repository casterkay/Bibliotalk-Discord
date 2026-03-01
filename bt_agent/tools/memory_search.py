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
    def __init__(self, *, emos_client: Any, segments_provider: SegmentsProvider, top_k: int = 8):
        self.emos_client = emos_client
        self.segments_provider = segments_provider
        self.top_k = top_k

    async def __call__(self, query: str, agent_id: str) -> list[Evidence]:
        search_result = await self.emos_client.search(
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

        evidences: list[Evidence] = []
        for segment in reranked:
            source_title = segment_rows[0].get("source_title", "Unknown Source")
            source_url = segment_rows[0].get("source_url", "")
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
