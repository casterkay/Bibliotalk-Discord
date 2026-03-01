from __future__ import annotations

from uuid import uuid4

import pytest

from bt_agent.agent_factory import create_clone_agent
from bt_common.citation import Evidence
from bt_common.matrix_helpers import format_clone_response


class FakeSupabase:
    def __init__(self, agent_id):
        self.agent_id = agent_id

    async def get_agent(self, agent_id):
        return {
            "id": str(agent_id),
            "display_name": "Confucius (Clone)",
            "persona_prompt": "You are Confucius.",
            "llm_model": "nova-lite-v2",
        }

    async def get_agent_emos_config(self, agent_id):
        return {"agent_id": str(agent_id), "emos_base_url": "https://emos.local"}

    async def get_segments_by_ids(self, segment_ids):
        return [
            {
                "id": str(segment_ids[0]),
                "agent_id": str(self.agent_id),
                "text": "Learning without thought is labor lost.",
            }
        ]


class FakeRegistry:
    def resolve(self, model: str):
        assert model == "nova-lite-v2"

        class _LLM:
            async def generate(self, *, persona_prompt: str, query: str, evidence: list[Evidence]) -> str:
                _ = persona_prompt
                _ = query
                _ = evidence
                return "Learning without thought is labor lost."

        return _LLM()

    def init_defaults(self):
        return None


@pytest.mark.asyncio
async def test_clone_text_chat_e2e() -> None:
    agent_id = uuid4()
    supabase = FakeSupabase(agent_id)

    evidence = Evidence(
        segment_id=uuid4(),
        emos_message_id="a:b:c:seg:1",
        source_title="The Analects",
        source_url="https://example.com",
        text="Learning without thought is labor lost.",
        platform="gutenberg",
    )

    async def memory_search(_query: str, _agent_id: str):
        return [evidence]

    agent = await create_clone_agent(
        agent_id,
        supabase_helpers=supabase,
        llm_registry=FakeRegistry(),
        memory_search_fn=memory_search,
    )

    response = await agent.run("What did you say about learning?")
    payload = format_clone_response(response["text"], response["citations"])

    assert payload["com.bibliotalk.citations"]["items"]
    assert "Sources:" in payload["body"]
