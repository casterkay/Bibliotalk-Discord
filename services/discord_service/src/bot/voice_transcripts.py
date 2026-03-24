from __future__ import annotations

import logging
from collections import deque
from typing import Any

import discord

logger = logging.getLogger("discord_service")


def _compact_text(value: str) -> str:
    return " ".join((value or "").split()).strip()


class VoiceTranscriptPublisher:
    def __init__(
        self,
        *,
        client: discord.Client,
        default_text_channel_id: str | None = None,
        logger_: logging.Logger | None = None,
    ) -> None:
        self._client = client
        self._default_text_channel_id = (default_text_channel_id or "").strip() or None
        self._logger = logger_ or logger
        self._recent_dedup: deque[tuple[str, str, str]] = deque(maxlen=128)

    async def publish_input(self, payload: dict[str, Any]) -> None:
        await self._publish(kind="input", payload=payload)

    async def publish_output(self, payload: dict[str, Any]) -> None:
        await self._publish(kind="output", payload=payload)

    async def _publish(self, *, kind: str, payload: dict[str, Any]) -> None:
        text = _compact_text(str(payload.get("text") or ""))
        if not text:
            return

        bridge_id = str(payload.get("bridge_id") or "")
        dedup_key = (bridge_id, kind, text)
        if dedup_key in self._recent_dedup:
            return
        self._recent_dedup.append(dedup_key)

        channel_id = str(
            payload.get("text_thread_id") or payload.get("text_channel_id") or ""
        ).strip()
        if not channel_id:
            channel_id = self._default_text_channel_id or ""
        if not channel_id:
            return

        channel = self._client.get_channel(int(channel_id))
        if channel is None:
            try:
                channel = await self._client.fetch_channel(int(channel_id))
            except Exception:
                self._logger.info(
                    "voice transcript channel fetch failed channel_id=%s bridge_id=%s kind=%s",
                    channel_id,
                    bridge_id,
                    kind,
                )
                return

        if not isinstance(channel, (discord.TextChannel, discord.Thread)):
            self._logger.info(
                "voice transcript channel unsupported channel_id=%s type=%s",
                channel_id,
                type(channel).__name__,
            )
            return

        tag = "🧑" if kind == "input" else "🤖"
        content = f"{tag} {text}"[:2000]
        await channel.send(content, allowed_mentions=discord.AllowedMentions.none())
