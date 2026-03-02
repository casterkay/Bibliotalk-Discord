"""Nova Sonic backend adapter (mockable local implementation)."""

from __future__ import annotations

import asyncio
from collections.abc import AsyncIterator

from .base import AudioChunk, EndOfTurn, Transcript, VoiceBackend, VoiceEvent


class NovaSonicBackend(VoiceBackend):
    def __init__(self, *, max_session_seconds: int = 8 * 60):
        self.max_session_seconds = max_session_seconds
        self._queue: asyncio.Queue[VoiceEvent] = asyncio.Queue()
        self._active = False

    async def start_session(self, system_prompt: str, tools: list[dict]) -> None:
        _ = system_prompt
        _ = tools
        self._active = True

    async def send_audio_chunk(self, pcm_16khz_bytes: bytes) -> None:
        if not self._active:
            return
        await self._queue.put(Transcript(text=f"heard {len(pcm_16khz_bytes)} bytes", role="user"))
        await self._queue.put(AudioChunk(pcm_24khz=pcm_16khz_bytes))
        await self._queue.put(EndOfTurn())

    async def receive(self) -> AsyncIterator[VoiceEvent]:
        while self._active:
            event = await self._queue.get()
            yield event
            if isinstance(event, EndOfTurn):
                break

    async def end_session(self) -> None:
        self._active = False
