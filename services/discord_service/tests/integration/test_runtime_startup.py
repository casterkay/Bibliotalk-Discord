from __future__ import annotations

import uuid

import pytest
from bt_common.evidence_store.engine import get_session_factory, init_database
from bt_common.evidence_store.models import DiscordMap, Figure
from discord_service.config import load_runtime_config
from discord_service.runtime import build_live_discord_runtime


@pytest.mark.anyio
async def test_discord_runtime_builds_single_bot_client(tmp_path) -> None:
    db = tmp_path / "bibliotalk.db"
    await init_database(db)
    session_factory = get_session_factory(db)

    async with session_factory() as session:
        figure = Figure(
            figure_id=uuid.uuid4(),
            display_name="Alan Watts",
            emos_user_id="alan-watts",
            status="active",
        )
        session.add(figure)
        await session.flush()
        session.add(
            DiscordMap(
                figure_id=figure.figure_id, guild_id="guild", channel_id="channel"
            )
        )
        await session.commit()

    config = load_runtime_config(db_path=str(db))
    runtime = await build_live_discord_runtime(config, session_factory=session_factory)

    assert runtime.client is not None
    assert runtime.client.figure_directory.resolve_token("alan-watts") is not None
