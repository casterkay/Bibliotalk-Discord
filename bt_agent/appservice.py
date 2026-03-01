"""Matrix-style message handling for clone responses."""

from __future__ import annotations

from typing import Any, Awaitable, Callable

from bt_agent.guards import RateLimiter
from bt_common.matrix_helpers import format_clone_response

AgentResolver = Callable[[str], Awaitable[Any]]
SendMessage = Callable[[str, dict[str, Any]], Awaitable[None]]
SaveHistory = Callable[[dict[str, Any]], Awaitable[None]]


class AppServiceHandler:
    def __init__(
        self,
        *,
        agent_resolver: AgentResolver,
        send_message: SendMessage,
        save_history: SaveHistory | None = None,
        rate_limiter: RateLimiter | None = None,
    ):
        self.agent_resolver = agent_resolver
        self.send_message = send_message
        self.save_history = save_history
        self.rate_limiter = rate_limiter or RateLimiter(cooldown_seconds=5)

    async def handle_event(self, event: dict[str, Any]) -> dict[str, Any] | None:
        if event.get("type") != "m.room.message":
            return None

        room_id = event.get("room_id", "")
        if not self.rate_limiter.allow(room_id):
            return None

        body = event.get("content", {}).get("body", "").strip()
        if not body:
            return None

        agent_id = event.get("agent_id")
        if not agent_id:
            return None

        agent = await self.agent_resolver(agent_id)
        response = await agent.run(body)
        payload = format_clone_response(response["text"], response["citations"])

        await self.send_message(room_id, payload)

        if self.save_history is not None:
            await self.save_history(
                {
                    "matrix_room_id": room_id,
                    "sender_agent_id": agent_id,
                    "sender_matrix_user_id": event.get("sender"),
                    "matrix_event_id": event.get("event_id"),
                    "modality": "text",
                    "content": response["text"],
                    "citations": payload["com.bibliotalk.citations"]["items"],
                }
            )

        return payload
