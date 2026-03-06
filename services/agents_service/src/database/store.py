"""Database access abstraction for agents_service.

The logical schema is defined in BLUEPRINT.md (relational/Postgres dialect).
For local E2E development we use SQLite via SQLAlchemy, so this interface is
intentionally small and focused on the queries required by the runtime and
bootstrap tooling.
"""

from __future__ import annotations

from typing import Protocol, TypedDict
from uuid import UUID


class AgentRow(TypedDict, total=False):
    id: str
    kind: str
    display_name: str
    matrix_user_id: str
    persona_prompt: str
    llm_model: str
    is_active: bool
    created_at: str | None


class AgentEmosConfigRow(TypedDict, total=False):
    agent_id: str
    emos_base_url: str
    emos_api_key_encrypted: str | None
    emos_api_key: str | None
    tenant_prefix: str


class SourceRow(TypedDict, total=False):
    id: str
    agent_id: str
    platform: str
    external_id: str
    external_url: str | None
    title: str
    author: str | None
    published_at: str | None
    emos_group_id: str


class SegmentRow(TypedDict, total=False):
    id: str
    agent_id: str
    source_id: str
    platform: str
    seq: int
    text: str
    sha256: str
    emos_message_id: str
    source_title: str | None
    source_url: str | None
    speaker: str | None
    start_ms: int | None
    end_ms: int | None
    matrix_event_id: str | None


class ChatHistoryRow(TypedDict, total=False):
    id: str
    matrix_room_id: str
    sender_agent_id: str | None
    sender_matrix_user_id: str
    matrix_event_id: str | None
    modality: str
    content: str
    citations: list[dict[str, object]]
    created_at: str


class Store(Protocol):
    async def aclose(self) -> None: ...

    # Agents / config
    async def get_agent(self, agent_id: UUID) -> AgentRow | None: ...
    async def get_agent_by_matrix_id(self, matrix_user_id: str) -> AgentRow | None: ...
    async def get_agent_emos_config(self, agent_id: UUID) -> AgentEmosConfigRow | None: ...

    # Rooms
    async def is_profile_room(self, matrix_room_id: str) -> bool: ...

    # Retrieval/citations
    async def get_sources_by_emos_group_ids(self, emos_group_ids: list[str]) -> list[SourceRow]: ...
    async def get_segments_by_source_ids(self, source_ids: list[str]) -> list[SegmentRow]: ...
    async def get_segments_by_ids(self, segment_ids: list[UUID]) -> list[SegmentRow]: ...
    async def get_segments_for_agent(self, agent_id: UUID) -> list[SegmentRow]: ...

    # Audit
    async def save_chat_history(self, record: ChatHistoryRow) -> ChatHistoryRow: ...
