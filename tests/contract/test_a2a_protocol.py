from __future__ import annotations

from uuid import uuid4

import pytest


@pytest.mark.asyncio
async def test_agent_card_matches_schema() -> None:
    from bt_agent.discussion.a2a_server import CloneA2AServer

    server = CloneA2AServer(
        clone_name="Confucius (Clone)",
        clone_description="Digital twin of Confucius",
        clone_id=str(uuid4()),
        invoke_clone=None,
    )

    card = server.agent_card()

    assert card["name"] == "Confucius (Clone)"
    assert "skills" in card
    assert card["capabilities"]["streaming"] is True


@pytest.mark.asyncio
async def test_tasks_send_request_and_completed_response_with_artifacts() -> None:
    from bt_agent.discussion.a2a_server import CloneA2AServer

    async def invoke_clone(_prompt: str):
        return {"text": "Answer", "citations": [{"index": 1}]}

    server = CloneA2AServer(
        clone_name="Confucius (Clone)",
        clone_description="Digital twin of Confucius",
        clone_id=str(uuid4()),
        invoke_clone=invoke_clone,
    )

    request = {
        "jsonrpc": "2.0",
        "id": "req-1",
        "method": "tasks/send",
        "params": {
            "id": "task-1",
            "message": {"role": "user", "parts": [{"type": "text", "text": "Discuss virtue"}]},
        },
    }

    response = await server.handle_jsonrpc(request)

    assert response["jsonrpc"] == "2.0"
    result = response["result"]
    assert result["status"]["state"] == "completed"
    assert result["artifacts"][0]["parts"][0]["type"] == "text"
    assert result["artifacts"][0]["parts"][1]["type"] == "data"


@pytest.mark.asyncio
async def test_task_lifecycle_states() -> None:
    from bt_agent.discussion.a2a_server import CloneA2AServer

    async def invoke_clone(_prompt: str):
        return {"text": "Answer", "citations": []}

    server = CloneA2AServer(
        clone_name="Confucius (Clone)",
        clone_description="Digital twin of Confucius",
        clone_id=str(uuid4()),
        invoke_clone=invoke_clone,
    )

    transitions = []

    def on_transition(task_id: str, state: str) -> None:
        transitions.append((task_id, state))

    server.on_transition = on_transition

    request = {
        "jsonrpc": "2.0",
        "id": "req-2",
        "method": "tasks/send",
        "params": {
            "id": "task-2",
            "message": {"role": "user", "parts": [{"type": "text", "text": "Discuss virtue"}]},
        },
    }

    await server.handle_jsonrpc(request)

    assert transitions == [("task-2", "submitted"), ("task-2", "working"), ("task-2", "completed")]
