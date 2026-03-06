"""Voice session lifecycle management."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any
from uuid import uuid4

from bt_common.exceptions import VoiceSessionError

from .backends.base import VoiceBackend
from .backends.gemini_live import GeminiLiveBackend
from .backends.nova_sonic import NovaSonicBackend


@dataclass
class VoiceSession:
    id: str
    agent_id: str
    room_id: str
    matrix_user_id: str | None
    backend_type: str
    backend: VoiceBackend
    state: str = "created"
    citations: list[dict[str, Any]] = field(default_factory=list)


class VoiceSessionManager:
    def __init__(self):
        self._sessions: dict[str, VoiceSession] = {}
        self._room_speakers: dict[str, str] = {}

    def _make_backend(self, backend_type: str) -> VoiceBackend:
        if backend_type == "nova_sonic":
            return NovaSonicBackend()
        if backend_type == "gemini_live":
            return GeminiLiveBackend()
        raise VoiceSessionError(f"Unsupported backend {backend_type}")

    async def create_session(
        self,
        agent_id: str,
        room_id: str,
        backend_type: str,
        *,
        matrix_user_id: str | None = None,
    ) -> VoiceSession:
        backend = self._make_backend(backend_type)
        session = VoiceSession(
            id=str(uuid4()),
            agent_id=agent_id,
            room_id=room_id,
            matrix_user_id=matrix_user_id,
            backend_type=backend_type,
            backend=backend,
            state="active",
        )
        await backend.start_session("voice ghost", tools=[])
        self._sessions[session.id] = session
        self._room_speakers[room_id] = agent_id
        return session

    async def create_multi_agent_session(
        self,
        agent_ids: list[str],
        room_id: str,
        backend_type: str,
    ) -> dict[str, VoiceSession]:
        sessions: dict[str, VoiceSession] = {}
        for agent_id in agent_ids:
            session = await self.create_session(agent_id, room_id, backend_type)
            sessions[agent_id] = session
        return sessions

    async def route_audio(self, room_id: str, pcm_16khz_bytes: bytes) -> None:
        active_speaker = self._room_speakers.get(room_id)
        if not active_speaker:
            return

        for session in self._sessions.values():
            if session.room_id != room_id:
                continue
            if session.agent_id == active_speaker:
                await session.backend.send_audio_chunk(pcm_16khz_bytes)

    def set_active_speaker(self, room_id: str, agent_id: str) -> None:
        self._room_speakers[room_id] = agent_id

    async def end_session(self, session_id: str) -> None:
        session = self._sessions.get(session_id)
        if not session:
            return
        await session.backend.end_session()
        session.state = "ended"

    def get_session(self, session_id: str) -> VoiceSession | None:
        return self._sessions.get(session_id)
