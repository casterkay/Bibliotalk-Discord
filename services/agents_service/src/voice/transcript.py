"""Voice transcript aggregation and posting."""

from __future__ import annotations

from collections.abc import Awaitable, Callable
from typing import Any

from ..matrix.appservice import format_ghost_response
from .backends.base import EndOfTurn, Transcript
from .session_manager import VoiceSession

PostMessage = Callable[[str, dict[str, Any]], Awaitable[None]]
SaveHistory = Callable[[dict[str, Any]], Awaitable[None]]


class TranscriptCollector:
    async def collect_and_post(
        self,
        session: VoiceSession,
        *,
        post_message: PostMessage,
        save_history: SaveHistory,
    ) -> None:
        buffer: list[str] = []
        async for event in session.backend.receive():
            if isinstance(event, Transcript):
                buffer.append(event.text)
            if isinstance(event, EndOfTurn):
                text = " ".join(buffer).strip()
                payload = format_ghost_response(text, [])
                await post_message(session.room_id, payload)
                await save_history(
                    {
                        "matrix_room_id": session.room_id,
                        "sender_agent_id": session.agent_id,
                        "sender_matrix_user_id": session.matrix_user_id or session.agent_id,
                        "matrix_event_id": None,
                        "modality": "voice",
                        "content": text,
                        "citations": [],
                    }
                )
                buffer.clear()
