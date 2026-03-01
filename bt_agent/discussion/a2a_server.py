"""Minimal A2A JSON-RPC server for a single clone."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Awaitable, Callable

InvokeClone = Callable[[str], Awaitable[dict[str, Any]]]


@dataclass
class CloneA2AServer:
    clone_name: str
    clone_description: str
    clone_id: str
    invoke_clone: InvokeClone | None
    on_transition: Callable[[str, str], None] | None = None

    def agent_card(self) -> dict[str, Any]:
        return {
            "name": self.clone_name,
            "description": self.clone_description,
            "version": "1.0",
            "skills": [
                {
                    "id": "grounded_conversation",
                    "name": "Grounded Conversation",
                    "description": "Respond to questions with memory-grounded citations.",
                    "input_modes": ["text/plain"],
                    "output_modes": ["application/json"],
                }
            ],
            "capabilities": {"streaming": True},
        }

    async def handle_jsonrpc(self, request: dict[str, Any]) -> dict[str, Any]:
        if request.get("method") != "tasks/send":
            return {
                "jsonrpc": "2.0",
                "id": request.get("id"),
                "error": {"code": -32601, "message": "Method not found"},
            }

        params = request.get("params", {})
        task_id = params.get("id", "")
        self._transition(task_id, "submitted")
        self._transition(task_id, "working")

        prompt = ""
        for part in params.get("message", {}).get("parts", []):
            if part.get("type") == "text":
                prompt += part.get("text", "")

        invoke = self.invoke_clone
        result = await invoke(prompt) if invoke is not None else {"text": "", "citations": []}

        response = {
            "jsonrpc": "2.0",
            "id": request.get("id"),
            "result": {
                "id": task_id,
                "status": {"state": "completed"},
                "artifacts": [
                    {
                        "parts": [
                            {"type": "text", "text": result.get("text", "")},
                            {"type": "data", "data": {"citations": result.get("citations", [])}},
                        ]
                    }
                ],
            },
        }
        self._transition(task_id, "completed")
        return response

    def _transition(self, task_id: str, state: str) -> None:
        if self.on_transition:
            self.on_transition(task_id, state)
