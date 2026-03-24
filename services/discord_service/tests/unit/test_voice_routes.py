from __future__ import annotations

import uuid
from dataclasses import dataclass
from pathlib import Path

import discord
import pytest

from discord_service.bot.client import BibliotalkDiscordClient
from discord_service.config import DiscordRuntimeConfig


@dataclass(frozen=True, slots=True)
class _FakeAgentInfo:
    agent_id: uuid.UUID
    agent_slug: str
    display_name: str
    persona_summary: str | None = None


class _FakeAgentDirectory:
    def __init__(self) -> None:
        self._agent = _FakeAgentInfo(
            agent_id=uuid.uuid4(),
            agent_slug="alan-watts",
            display_name="Alan Watts",
        )

    def list_agents(self):
        return [self._agent]

    def resolve_token(self, token: str):
        if token in {"alan-watts", "Alan Watts"}:
            return self._agent
        return None

    def resolve_override_prefix(self, _content: str):
        return None


class _FakeTalkService:
    async def start_talk(self, **_kwargs):
        raise NotImplementedError

    async def list_talks(self, **_kwargs):
        return []

    async def handle_thread_message(self, **_kwargs):
        return False


class _FakeVoiceProxy:
    def __init__(self) -> None:
        self._rows = []

    async def ensure_bridge(self, **_kwargs):
        raise NotImplementedError

    async def stop_guild(self, **_kwargs):
        return False

    async def status(self, *, guild_id: str | None = None):
        _ = guild_id
        return self._rows

    async def forward_gateway_dispatch(self, **_kwargs):
        return None

    async def stop_all(self, *, reason: str = "shutdown"):
        _ = reason
        return None


class _FakeResponse:
    def __init__(self) -> None:
        self.messages: list[tuple[str, dict]] = []

    async def send_message(self, content: str, **kwargs) -> None:
        self.messages.append((content, kwargs))


class _FakeMember:
    def __init__(self, member_id: int, voice=None) -> None:
        self.id = member_id
        self.voice = voice


class _FakeGuild:
    def __init__(self, guild_id: int, member: _FakeMember) -> None:
        self.id = guild_id
        self._member = member

    def get_member(self, user_id: int):
        if self._member.id == user_id:
            return self._member
        return None


class _FakeUser:
    def __init__(self, user_id: int) -> None:
        self.id = user_id


class _FakeInteraction:
    def __init__(self, *, guild, user, channel=None) -> None:
        self.guild = guild
        self.user = user
        self.channel = channel
        self.response = _FakeResponse()


def _build_client() -> BibliotalkDiscordClient:
    config = DiscordRuntimeConfig(
        db_path=Path("/tmp/bibliotalk-test.db"),
        log_level="INFO",
        discord_command_guild_id=None,
        voip_service_url="http://localhost:9012",
        discord_voice_default_text_channel_id=None,
    )
    return BibliotalkDiscordClient(
        config=config,
        talk_service=_FakeTalkService(),
        agent_directory=_FakeAgentDirectory(),
        voice_gateway_proxy=_FakeVoiceProxy(),
        intents=discord.Intents.none(),
    )


@pytest.mark.anyio
async def test_voice_join_requires_user_in_voice_channel() -> None:
    client = _build_client()
    interaction = _FakeInteraction(
        guild=_FakeGuild(guild_id=1, member=_FakeMember(member_id=11, voice=None)),
        user=_FakeUser(11),
    )

    await client._cmd_voice_join(interaction, agent=None, text_channel=None)

    assert interaction.response.messages
    assert "Join a voice channel first." in interaction.response.messages[0][0]
    await client.close()


@pytest.mark.anyio
async def test_voice_status_reports_active_bridge() -> None:
    client = _build_client()
    assert client.voice_gateway_proxy is not None
    client.voice_gateway_proxy._rows = [
        {
            "bridge_id": "discord:1:2:3",
            "agent_id": "3",
            "voice_channel_id": "2",
            "guild_id": "1",
            "text_channel_id": None,
            "text_thread_id": None,
        }
    ]
    interaction = _FakeInteraction(
        guild=_FakeGuild(guild_id=1, member=_FakeMember(member_id=11, voice=None)),
        user=_FakeUser(11),
    )

    await client._cmd_voice_status(interaction)

    assert interaction.response.messages
    content = interaction.response.messages[0][0]
    assert "discord:1:2:3" in content
    assert "<#2>" in content
    await client.close()
