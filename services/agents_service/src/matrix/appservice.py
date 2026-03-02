"""Matrix-style message handling for ghost responses."""

from __future__ import annotations

from html import escape
from typing import Any, Awaitable, Callable

from ..models.citation import Citation
from .guards import RateLimiter

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
        payload = format_ghost_response(response["text"], response["citations"])

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


def format_ghost_response(text: str, citations: list[Citation]) -> dict:
    marker_text = text
    html_text = escape(text)

    source_lines = ["", "----------", "Sources:"]
    html_sources = ["<hr><b>Sources:</b><br>"]

    for citation in citations:
        marker = f"[^ {citation.index}]".replace(" ", "")
        if marker not in marker_text:
            marker_text += f" {marker}"
        html_text += f" <sup>[{citation.index}]</sup>"
        source_lines.append(
            f"[{citation.index}] {citation.source_title} ({citation.platform})"
        )
        html_sources.append(
            f'[{citation.index}] <a href="{escape(citation.source_url)}">{escape(citation.source_title)}</a><br>'
        )

    return {
        "msgtype": "m.text",
        "body": "\n".join([marker_text, *source_lines]),
        "format": "org.matrix.custom.html",
        "formatted_body": f"{html_text}{''.join(html_sources)}",
        "com.bibliotalk.citations": {
            "version": "1",
            "items": [citation.model_dump(mode="json") for citation in citations],
        },
    }
