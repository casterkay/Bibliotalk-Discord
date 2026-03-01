from __future__ import annotations

from uuid import uuid4

import pytest

from bt_agent.discussion.a2a_server import CloneA2AServer
from bt_agent.discussion.orchestrator import DiscussionConfig, DiscussionOrchestrator


@pytest.mark.asyncio
async def test_multi_agent_discussion_flow() -> None:
    agent_a = str(uuid4())
    agent_b = str(uuid4())

    async def invoke_a(_prompt: str):
        return {"text": "A response", "citations": [{"agent": agent_a}]}

    async def invoke_b(_prompt: str):
        return {"text": "B response", "citations": [{"agent": agent_b}]}

    servers = {
        agent_a: CloneA2AServer("A", "A desc", agent_a, invoke_a),
        agent_b: CloneA2AServer("B", "B desc", agent_b, invoke_b),
    }

    async def a2a_client(clone_id: str, request: dict):
        return await servers[clone_id].handle_jsonrpc(request)

    posted: list[dict] = []

    async def post_message(_room_id: str, payload: dict):
        posted.append(payload)

    orchestrator = DiscussionOrchestrator(a2a_client=a2a_client, post_message=post_message)
    config = DiscussionConfig(topic="virtue", clone_agent_ids=[agent_a, agent_b], max_turns=3)

    history = await orchestrator.run("!room:example", config)

    assert len(history) == 3
    assert {item["clone_id"] for item in history} == {agent_a, agent_b}
    assert len(posted) == 3
    for item in history:
        for citation in item["citations"]:
            assert citation["agent"] == item["clone_id"]
