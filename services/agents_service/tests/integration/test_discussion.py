from __future__ import annotations

from uuid import uuid4

import pytest
from agents_service.agent.orchestrator import DiscussionConfig, DiscussionOrchestrator


@pytest.mark.anyio
async def test_multi_agent_discussion_flow() -> None:
    agent_a = str(uuid4())
    agent_b = str(uuid4())

    async def a2a_client(ghost_id: str, request: dict):
        _ = request
        if ghost_id == agent_a:
            return {
                "result": {
                    "artifacts": [
                        {
                            "parts": [
                                {"text": "A response"},
                                {"data": {"citations": [{"agent": agent_a}]}},
                            ]
                        }
                    ]
                }
            }
        return {
            "result": {
                "artifacts": [
                    {
                        "parts": [
                            {"text": "B response"},
                            {"data": {"citations": [{"agent": agent_b}]}},
                        ]
                    }
                ]
            }
        }

    posted: list[dict] = []

    async def post_message(_room_id: str, payload: dict):
        posted.append(payload)

    orchestrator = DiscussionOrchestrator(a2a_client=a2a_client, post_message=post_message)
    config = DiscussionConfig(topic="virtue", ghost_agent_ids=[agent_a, agent_b], max_turns=3)

    history = await orchestrator.run("!room:example", config)

    assert len(history) == 3
    assert {item["ghost_id"] for item in history} == {agent_a, agent_b}
    assert len(posted) == 3
    for item in history:
        for citation in item["citations"]:
            assert citation["agent"] == item["ghost_id"]
