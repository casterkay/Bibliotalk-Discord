"""Clone agent factory and lightweight runtime."""

from __future__ import annotations

import asyncio
import time
from dataclasses import dataclass
from typing import Any, Awaitable, Callable
from uuid import UUID

from bt_agent.llm_registry import LLMRegistry
from bt_agent.tools.emit_citations import EmitCitationsTool
from bt_agent.tools.memory_search import MemorySearchTool
from bt_common.config import get_emos_fallback_settings
from bt_common.citation import Evidence
from bt_common.emos_client import EMOSClient
from bt_common.exceptions import AgentNotFoundError
from bt_common.supabase_helpers import SupabaseHelpers

MemorySearchFn = Callable[[str, str], Awaitable[list[Evidence]]]
EmitCitationsFn = Callable[[list[Evidence], str], Awaitable[list]]

_CACHE: dict[str, tuple[float, "CloneAgent"]] = {}
_CACHE_LOCK = asyncio.Lock()


@dataclass
class CloneAgent:
    id: str
    name: str
    instruction: str
    model: str
    llm: Any
    memory_search_fn: MemorySearchFn
    emit_citations_fn: EmitCitationsFn

    async def run(self, query: str) -> dict[str, Any]:
        evidence = await self.memory_search_fn(query, self.id)
        if not evidence:
            return {"text": "I have no evidence to answer that right now.", "citations": []}

        text = await self.llm.generate(persona_prompt=self.instruction, query=query, evidence=evidence)
        citations = await self.emit_citations_fn(evidence, self.id)
        return {"text": text, "citations": citations}


async def create_clone_agent(
    agent_id: UUID,
    *,
    supabase_helpers: SupabaseHelpers | Any,
    llm_registry: Any | None = None,
    memory_search_fn: MemorySearchFn | None = None,
    emit_citations_fn: EmitCitationsFn | None = None,
    cache_ttl_seconds: int = 60,
) -> CloneAgent:
    key = str(agent_id)
    now = time.time()

    async with _CACHE_LOCK:
        cached = _CACHE.get(key)
        if cached and (now - cached[0]) < cache_ttl_seconds:
            return cached[1]

    agent_row = await supabase_helpers.get_agent(agent_id)
    if not agent_row:
        raise AgentNotFoundError(f"Agent {agent_id} not found")

    emos_config = await supabase_helpers.get_agent_emos_config(agent_id) or {}
    emos_fallback = get_emos_fallback_settings()
    emos_client = EMOSClient(
        emos_config.get("emos_base_url") or emos_fallback.EMOS_BASE_URL or "",
        api_key=(
            emos_config.get("emos_api_key_encrypted")
            or emos_config.get("emos_api_key")
            or emos_fallback.EMOS_API_KEY
        ),
    )

    if memory_search_fn is None:
        memory_tool = MemorySearchTool(
            emos_client=emos_client,
            segments_provider=lambda _agent_id: supabase_helpers.get_segments_for_agent(UUID(_agent_id)),
        )
        memory_search_fn = memory_tool

    if emit_citations_fn is None:
        emit_tool = EmitCitationsTool(
            segments_by_ids_provider=lambda segment_ids: supabase_helpers.get_segments_by_ids(segment_ids)
        )
        emit_citations_fn = emit_tool

    registry = llm_registry or LLMRegistry
    if hasattr(registry, "init_defaults"):
        registry.init_defaults()
    model = agent_row.get("llm_model", "gemini-2.5-flash")
    llm = registry.resolve(model)

    clone = CloneAgent(
        id=key,
        name=agent_row["display_name"],
        instruction=agent_row["persona_prompt"],
        model=model,
        llm=llm,
        memory_search_fn=memory_search_fn,
        emit_citations_fn=emit_citations_fn,
    )

    async with _CACHE_LOCK:
        _CACHE[key] = (time.time(), clone)
    return clone
