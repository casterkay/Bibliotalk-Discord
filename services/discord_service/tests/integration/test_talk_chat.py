from __future__ import annotations

import uuid
from datetime import UTC, datetime
from importlib import import_module

import pytest
from bt_common.evidence_store.engine import get_session_factory, init_database
from bt_common.evidence_store.models import Figure, TalkParticipant, TalkThread


class FakeAgent:
    def __init__(self, response_text: str, evidence: list[object]) -> None:
        self.response_text = response_text
        self.evidence = evidence

    async def run(self, query: str) -> dict:
        _ = query
        return {"text": self.response_text, "citations": [], "evidence": self.evidence}


class FakeTransport:
    def __init__(self) -> None:
        self.persona_messages: list[tuple[str, str, str]] = []
        self.bot_messages: list[tuple[str, str]] = []

    async def list_eligible_guilds(self, *, hub_channel_name: str):
        raise NotImplementedError

    async def resolve_hub_channel_id(
        self, *, guild_id: str, hub_channel_name: str
    ) -> str:
        raise NotImplementedError

    async def create_private_thread(
        self,
        *,
        hub_channel_id: str,
        name: str,
        auto_archive_duration_minutes: int,
        invitable: bool,
    ) -> str:
        raise NotImplementedError

    async def add_user_to_thread(self, *, thread_id: str, discord_user_id: str) -> None:
        return None

    async def send_bot_message(self, *, thread_id: str, content: str) -> str:
        self.bot_messages.append((thread_id, content))
        return "msg-1"

    async def pin_message(self, *, thread_id: str, message_id: str) -> None:
        return None

    async def send_persona_message(
        self,
        *,
        guild_id: str,
        hub_channel_id: str,
        thread_id: str,
        persona_name: str,
        content: str,
        avatar_url: str | None = None,
    ) -> None:
        _ = avatar_url
        self.persona_messages.append((persona_name, thread_id, content))

    async def thread_exists(self, *, thread_id: str) -> bool:
        return True


@pytest.mark.anyio
async def test_talk_message_sends_grounded_character_reply(tmp_path) -> None:
    Evidence = import_module("agents_service.models.citation").Evidence
    DMOrchestrator = import_module("agents_service.agent.orchestrator").DMOrchestrator
    FigureDirectory = import_module("discord_service.talks.directory").FigureDirectory
    FacilitatorRouter = import_module("discord_service.talks.router").FacilitatorRouter
    TalkService = import_module("discord_service.talks.service").TalkService

    db = tmp_path / "bibliotalk.db"
    await init_database(db)
    session_factory = get_session_factory(db)

    figure_id = uuid.uuid4()
    evidence = Evidence(
        segment_id=uuid.uuid4(),
        figure_id=figure_id,
        memory_user_id="alan-watts",
        memory_timestamp=datetime(2026, 3, 8, 12, 0, 0, tzinfo=UTC),
        source_title="Alan Watts Lecture",
        source_url="https://www.youtube.com/watch?v=abc123",
        text="Learning without thought is labor lost.",
        platform="youtube",
    )

    async def create_agent(_: uuid.UUID) -> FakeAgent:
        return FakeAgent(
            f"He said [Learning without thought is labor lost.]({evidence.memory_url})",
            [evidence],
        )

    async with session_factory() as session:
        session.add(
            Figure(
                figure_id=figure_id,
                display_name="Alan Watts",
                emos_user_id="alan-watts",
                status="active",
            )
        )
        talk_id = uuid.uuid4()
        session.add(
            TalkThread(
                talk_id=talk_id,
                owner_discord_user_id="user-1",
                guild_id="guild-1",
                hub_channel_id="hub-1",
                thread_id="thread-1",
                status="open",
                created_at=datetime.now(tz=UTC),
                last_activity_at=datetime.now(tz=UTC),
            )
        )
        session.add(
            TalkParticipant(talk_id=talk_id, figure_id=figure_id, display_order=0)
        )
        await session.commit()

    directory = FigureDirectory(session_factory=session_factory)
    await directory.refresh()

    orchestrator = DMOrchestrator(agent_factory=create_agent)
    router = FacilitatorRouter()
    transport = FakeTransport()
    service = TalkService(
        session_factory=session_factory,
        figure_directory=directory,
        router=router,
        orchestrator=orchestrator,
        transport=transport,
        hub_channel_name="bibliotalk",
    )

    handled = await service.handle_thread_message(
        guild_id="guild-1",
        thread_id="thread-1",
        author_discord_user_id="user-1",
        content="What did he say about learning?",
    )

    assert handled is True
    assert transport.persona_messages
    assert evidence.memory_url in transport.persona_messages[0][2]


@pytest.mark.anyio
async def test_talk_message_falls_back_to_no_evidence_when_link_invalid(
    tmp_path,
) -> None:
    citation_module = import_module("agents_service.models.citation")
    Evidence = citation_module.Evidence
    NO_EVIDENCE_RESPONSE = citation_module.NO_EVIDENCE_RESPONSE
    DMOrchestrator = import_module("agents_service.agent.orchestrator").DMOrchestrator
    FigureDirectory = import_module("discord_service.talks.directory").FigureDirectory
    FacilitatorRouter = import_module("discord_service.talks.router").FacilitatorRouter
    TalkService = import_module("discord_service.talks.service").TalkService

    db = tmp_path / "bibliotalk.db"
    await init_database(db)
    session_factory = get_session_factory(db)

    figure_id = uuid.uuid4()
    evidence = Evidence(
        segment_id=uuid.uuid4(),
        figure_id=figure_id,
        memory_user_id="alan-watts",
        memory_timestamp=datetime(2026, 3, 8, 12, 0, 0, tzinfo=UTC),
        source_title="Alan Watts Lecture",
        source_url="https://www.youtube.com/watch?v=abc123",
        text="Learning without thought is labor lost.",
        platform="youtube",
    )

    async def create_agent(_: uuid.UUID) -> FakeAgent:
        return FakeAgent(
            f"He said [Fabricated quote]({evidence.memory_url})",
            [evidence],
        )

    async with session_factory() as session:
        session.add(
            Figure(
                figure_id=figure_id,
                display_name="Alan Watts",
                emos_user_id="alan-watts",
                status="active",
            )
        )
        talk_id = uuid.uuid4()
        session.add(
            TalkThread(
                talk_id=talk_id,
                owner_discord_user_id="user-1",
                guild_id="guild-1",
                hub_channel_id="hub-1",
                thread_id="thread-1",
                status="open",
                created_at=datetime.now(tz=UTC),
                last_activity_at=datetime.now(tz=UTC),
            )
        )
        session.add(
            TalkParticipant(talk_id=talk_id, figure_id=figure_id, display_order=0)
        )
        await session.commit()

    directory = FigureDirectory(session_factory=session_factory)
    await directory.refresh()

    orchestrator = DMOrchestrator(agent_factory=create_agent)
    router = FacilitatorRouter()
    transport = FakeTransport()
    service = TalkService(
        session_factory=session_factory,
        figure_directory=directory,
        router=router,
        orchestrator=orchestrator,
        transport=transport,
        hub_channel_name="bibliotalk",
    )

    handled = await service.handle_thread_message(
        guild_id="guild-1",
        thread_id="thread-1",
        author_discord_user_id="user-1",
        content="What did he say about learning?",
    )

    assert handled is True
    assert transport.persona_messages
    assert transport.persona_messages[0][2] == NO_EVIDENCE_RESPONSE
