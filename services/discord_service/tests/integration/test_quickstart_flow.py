from __future__ import annotations

import importlib.util
from pathlib import Path

import pytest
from bt_common.evidence_store.engine import get_session_factory, init_database
from bt_common.evidence_store.models import DiscordMap, Figure, Subscription
from discord_service.config import load_runtime_config
from discord_service.runtime import build_runtime_context
from sqlalchemy import select

ROOT = Path(__file__).resolve().parents[4]
SEED_SCRIPT = ROOT / "services" / "discord_service" / "scripts" / "seed_figure.py"


def _load_seed_module():
    spec = importlib.util.spec_from_file_location("seed_figure_script", SEED_SCRIPT)
    if spec is None or spec.loader is None:
        raise RuntimeError("Failed to load seed_figure.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@pytest.mark.anyio
async def test_quickstart_seed_script_creates_runtime_rows(tmp_path) -> None:
    db = tmp_path / "bibliotalk.db"
    await init_database(db)
    seed_module = _load_seed_module()

    await seed_module.seed_figure(
        db_path=str(db),
        figure_slug="alan-watts",
        display_name="Alan Watts",
        persona_summary="Figure bot used for quickstart validation.",
        subscription_url="https://www.youtube.com/@AlanWattsOrg",
        subscription_type="channel",
        guild_id="guild-1",
        channel_id="channel-1",
        poll_interval_minutes=30,
    )
    await seed_module.seed_figure(
        db_path=str(db),
        figure_slug="alan-watts",
        display_name="Alan Watts",
        persona_summary="Figure bot used for quickstart validation.",
        subscription_url="https://www.youtube.com/@AlanWattsOrg",
        subscription_type="channel",
        guild_id="guild-1",
        channel_id="channel-2",
        poll_interval_minutes=60,
    )

    session_factory = get_session_factory(db)
    async with session_factory() as session:
        figures = (await session.execute(select(Figure))).scalars().all()
        subscriptions = (await session.execute(select(Subscription))).scalars().all()
        discord_maps = (await session.execute(select(DiscordMap))).scalars().all()

    assert len(figures) == 1
    assert len(subscriptions) == 1
    assert len(discord_maps) == 1
    assert subscriptions[0].poll_interval_minutes == 60
    assert discord_maps[0].channel_id == "channel-2"

    config = load_runtime_config(db_path=str(db), figure_slug="alan-watts")
    context = await build_runtime_context(config, session_factory=session_factory)

    assert context.figure_found is True
    assert context.figure_slug == "alan-watts"
    assert context.channel_id == "channel-2"
