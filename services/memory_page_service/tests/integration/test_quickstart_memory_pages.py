from __future__ import annotations

import importlib.util
import uuid
from datetime import UTC, datetime
from pathlib import Path

import pytest
from bt_store.engine import get_session_factory, init_database
from bt_store.models_core import Agent
from bt_store.models_evidence import Segment, Source
from bt_store.models_ingestion import SourceIngestionState
from fastapi.testclient import TestClient
from memory_page_service.app import create_app
from memory_page_service.config import load_runtime_config
from sqlalchemy import select

ROOT = Path(__file__).resolve().parents[4]
TRIGGER_SCRIPT = (
    ROOT / "services" / "ingestion_service" / "scripts" / "trigger_ingest.py"
)


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


def _load_trigger_module():
    spec = importlib.util.spec_from_file_location(
        "trigger_ingest_script", TRIGGER_SCRIPT
    )
    if spec is None or spec.loader is None:
        raise RuntimeError("Failed to load trigger_ingest.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@pytest.mark.anyio
async def test_quickstart_memory_page_and_manual_trigger(tmp_path) -> None:
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

    trigger_module = _load_trigger_module()
    await trigger_module.trigger_manual_ingest(
        db_path=str(db),
        figure_slug="alan-watts",
        video_id="abc123",
        title="Alan Watts Lecture",
        source_url=None,
    )

    async with session_factory() as session:
        source = (
            (
                await session.execute(
                    select(Source).where(
                        Source.external_id == "abc123",
                        Source.content_platform == "youtube",
                    )
                )
            )
            .scalars()
            .first()
        )

    assert source is not None
    async with session_factory() as session:
        state = await session.get(SourceIngestionState, source.source_id)
    assert state is not None
    assert state.manual_requested_at is not None

    config = load_runtime_config(db_path=str(db))
    client = TestClient(create_app(config, evermemos_client=FakeEverMemOS()))
    response = client.get("/memory/alan-watts_20260308T120000Z")

    assert response.status_code == 200
    assert "Open the source video at this timepoint" in response.text
    assert "abc123&amp;t=60s" in response.text
