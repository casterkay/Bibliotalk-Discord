"""Discussion orchestrator for multi-ghost turn-taking."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Awaitable, Callable
from uuid import uuid4

A2AClient = Callable[[str, dict[str, Any]], Awaitable[dict[str, Any]]]
PostMessage = Callable[[str, dict[str, Any]], Awaitable[None]]


@dataclass
class DiscussionConfig:
    topic: str
    ghost_agent_ids: list[str]
    max_turns: int = 4
    turn_order: str = "round-robin"
    voice_mode: bool = False


class DiscussionOrchestrator:
    def __init__(
        self,
        *,
        a2a_client: A2AClient,
        post_message: PostMessage,
        voice_dispatch: Callable[[str, dict[str, Any]], Awaitable[None]] | None = None,
    ):
        self.a2a_client = a2a_client
        self.post_message = post_message
        self.voice_dispatch = voice_dispatch

    async def run(self, room_id: str, config: DiscussionConfig) -> list[dict[str, Any]]:
        history: list[dict[str, Any]] = []
        if not config.ghost_agent_ids:
            return history

        for turn in range(config.max_turns):
            ghost_id = config.ghost_agent_ids[turn % len(config.ghost_agent_ids)]
            context_lines = [config.topic] + [item["text"] for item in history]
            prompt = "\n".join(context_lines)

            request = {
                "jsonrpc": "2.0",
                "id": str(uuid4()),
                "method": "tasks/send",
                "params": {
                    "id": str(uuid4()),
                    "message": {
                        "role": "user",
                        "parts": [{"type": "text", "text": prompt}],
                    },
                },
            }
            response = await self.a2a_client(ghost_id, request)
            artifacts = response["result"]["artifacts"][0]["parts"]
            text = artifacts[0]["text"]
            citations = artifacts[1]["data"].get("citations", [])

            turn_payload = {"ghost_id": ghost_id, "text": text, "citations": citations}
            history.append(turn_payload)

            if config.voice_mode and self.voice_dispatch is not None:
                await self.voice_dispatch(room_id, turn_payload)
            else:
                await self.post_message(room_id, turn_payload)

        return history
