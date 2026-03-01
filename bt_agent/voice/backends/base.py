"""Voice backend abstract interface."""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import AsyncIterator


@dataclass
class AudioChunk:
    pcm_24khz: bytes


@dataclass
class ToolCall:
    tool_name: str
    args: dict


@dataclass
class Transcript:
    text: str
    role: str


@dataclass
class EndOfTurn:
    pass


VoiceEvent = AudioChunk | ToolCall | Transcript | EndOfTurn


class VoiceBackend(ABC):
    @abstractmethod
    async def start_session(self, system_prompt: str, tools: list[dict]) -> None:
        raise NotImplementedError

    @abstractmethod
    async def send_audio_chunk(self, pcm_16khz_bytes: bytes) -> None:
        raise NotImplementedError

    @abstractmethod
    async def receive(self) -> AsyncIterator[VoiceEvent]:
        raise NotImplementedError

    @abstractmethod
    async def end_session(self) -> None:
        raise NotImplementedError
