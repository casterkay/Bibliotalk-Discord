from __future__ import annotations

import uuid
from datetime import UTC, datetime

import pytest
from bt_store.engine import get_session_factory, init_database
from bt_store.models_core import Agent
from bt_store.models_evidence import Segment, Source
from fastapi.testclient import TestClient
from memory_page_service.app import create_app
from memory_page_service.config import load_runtime_config


class FakeEverMemOS:
    async def get_memories(self, **kwargs):
        return {
            "result": {
                "memories": [
                    {
                        "user_id": kwargs["user_id"],
                        "timestamp": kwargs["start_time"],
                        "summary": "Discussed learning",
                        "content": "Learning without thought is labor lost.",
                    }
                ]
            }
        }


@pytest.mark.anyio
async def test_memory_page_http_route_renders_html(tmp_path) -> None:
    db = tmp_path / "bibliotalk.db"
    await init_database(db)
    session_factory = get_session_factory(db)
    timestamp = datetime(2026, 3, 8, 12, 0, 0, tzinfo=UTC)

    async with session_factory() as session:
        agent = Agent(
            agent_id=uuid.uuid4(), display_name="Alan Watts", slug="alan-watts"
        )
        session.add(agent)
        await session.flush()
        source = Source(
            agent_id=agent.agent_id,
            content_platform="youtube",
            external_id="abc123",
            emos_group_id="alan-watts:youtube:abc123",
            title="Alan Watts Lecture",
            external_url="https://www.youtube.com/watch?v=abc123",
            published_at=datetime(2026, 3, 8, 11, 59, 0, tzinfo=UTC),
        )
        session.add(source)
        await session.flush()
        session.add(
            Segment(
                source_id=source.source_id,
                agent_id=agent.agent_id,
                seq=0,
                text="Learning without thought is labor lost.",
                sha256="a" * 64,
                start_ms=60_000,
                end_ms=62_000,
                create_time=timestamp,
                emos_message_id="alan-watts:youtube:abc123:seg:0",
            )
        )
        await session.commit()

    config = load_runtime_config(db_path=str(db))
    client = TestClient(create_app(config, evermemos_client=FakeEverMemOS()))

    response = client.get("/memory/alan-watts_20260308T120000Z")

    assert response.status_code == 200
    assert "Alan Watts Lecture" in response.text
    assert "Open the source video at this timepoint" in response.text
