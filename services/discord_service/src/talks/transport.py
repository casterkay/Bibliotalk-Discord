from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Protocol

import discord

logger = logging.getLogger("discord_service")


@dataclass(frozen=True, slots=True)
class EligibleGuild:
    guild_id: str
    name: str


class TalkTransport(Protocol):
    async def list_eligible_guilds(
        self, *, hub_channel_name: str
    ) -> list[EligibleGuild]: ...
    async def resolve_hub_channel_id(
        self, *, guild_id: str, hub_channel_name: str
    ) -> str: ...
    async def create_private_thread(
        self,
        *,
        hub_channel_id: str,
        name: str,
        auto_archive_duration_minutes: int,
        invitable: bool,
    ) -> str: ...
    async def add_user_to_thread(
        self, *, thread_id: str, discord_user_id: str
    ) -> None: ...
    async def send_bot_message(self, *, thread_id: str, content: str) -> str: ...
    async def pin_message(self, *, thread_id: str, message_id: str) -> None: ...
    async def send_persona_message(
        self,
        *,
        guild_id: str,
        hub_channel_id: str,
        thread_id: str,
        persona_name: str,
        content: str,
        avatar_url: str | None = None,
    ) -> None: ...
    async def thread_exists(self, *, thread_id: str) -> bool: ...


class DiscordPyTalkTransport:
    def __init__(
        self,
        *,
        client: discord.Client | None,
        logger_: logging.Logger | None = None,
        webhook_name: str = "bibliotalk-personas",
    ) -> None:
        self.client = client
        self._logger = logger_ or logger
        self._webhook_name = webhook_name
        self._webhook_cache: dict[tuple[str, str], discord.Webhook] = {}

    async def list_eligible_guilds(
        self, *, hub_channel_name: str
    ) -> list[EligibleGuild]:
        client = self._require_client()
        eligible: list[EligibleGuild] = []
        for guild in client.guilds:
            hub = self._find_text_channel_by_name(guild, hub_channel_name)
            if hub is None:
                continue
            if not self._can_create_private_threads(guild, hub):
                continue
            eligible.append(EligibleGuild(guild_id=str(guild.id), name=guild.name))
        return sorted(eligible, key=lambda item: item.name.lower())

    async def resolve_hub_channel_id(
        self, *, guild_id: str, hub_channel_name: str
    ) -> str:
        client = self._require_client()
        guild = client.get_guild(int(guild_id))
        if guild is None:
            raise LookupError(f"Bot is not in guild {guild_id}")
        hub = self._find_text_channel_by_name(guild, hub_channel_name)
        if hub is None:
            raise LookupError(f"Guild {guild_id} missing #{hub_channel_name} channel")
        if not self._can_create_private_threads(guild, hub):
            raise PermissionError(
                f"Bot lacks permission to create private threads in #{hub_channel_name}"
            )
        return str(hub.id)

    async def create_private_thread(
        self,
        *,
        hub_channel_id: str,
        name: str,
        auto_archive_duration_minutes: int,
        invitable: bool,
    ) -> str:
        hub = await self._get_text_channel(hub_channel_id)
        thread = await hub.create_thread(
            name=name[:100],
            type=discord.ChannelType.private_thread,
            invitable=invitable,
            auto_archive_duration=auto_archive_duration_minutes,
        )
        return str(thread.id)

    async def add_user_to_thread(self, *, thread_id: str, discord_user_id: str) -> None:
        thread = await self._get_thread(thread_id)
        await thread.add_user(discord.Object(id=int(discord_user_id)))

    async def send_bot_message(self, *, thread_id: str, content: str) -> str:
        thread = await self._get_thread(thread_id)
        message = await thread.send(
            content[:2000],
            allowed_mentions=discord.AllowedMentions.none(),
        )
        return str(message.id)

    async def pin_message(self, *, thread_id: str, message_id: str) -> None:
        thread = await self._get_thread(thread_id)
        message = await thread.fetch_message(int(message_id))
        await message.pin()

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
        try:
            webhook = await self._get_or_create_webhook(
                guild_id=guild_id, hub_channel_id=hub_channel_id
            )
        except Exception:
            webhook = None

        if webhook is None:
            await self.send_bot_message(
                thread_id=thread_id,
                content=f"**{persona_name}**: {content}".strip()[:2000],
            )
            return

        await webhook.send(
            content[:2000],
            username=persona_name[:80],
            avatar_url=avatar_url,
            allowed_mentions=discord.AllowedMentions.none(),
            thread=discord.Object(id=int(thread_id)),
            wait=False,
        )

    async def thread_exists(self, *, thread_id: str) -> bool:
        client = self._require_client()
        channel = client.get_channel(int(thread_id))
        if isinstance(channel, discord.Thread):
            return True
        try:
            fetched = await client.fetch_channel(int(thread_id))
        except Exception:
            return False
        return isinstance(fetched, discord.Thread)

    def _require_client(self) -> discord.Client:
        if self.client is None:
            raise RuntimeError("Discord client not initialized")
        return self.client

    def _find_text_channel_by_name(
        self, guild: discord.Guild, name: str
    ) -> discord.TextChannel | None:
        target = (name or "").strip().lower()
        if not target:
            return None
        for channel in guild.text_channels:
            if channel.name.lower() == target:
                return channel
        return None

    def _can_create_private_threads(
        self, guild: discord.Guild, channel: discord.TextChannel
    ) -> bool:
        client = self._require_client()
        member = guild.me or guild.get_member(client.user.id if client.user else 0)
        if member is None:
            return False
        perms = channel.permissions_for(member)
        return bool(perms.create_private_threads and perms.send_messages)

    async def _get_text_channel(self, channel_id: str) -> discord.TextChannel:
        client = self._require_client()
        channel = client.get_channel(int(channel_id))
        if channel is None:
            channel = await client.fetch_channel(int(channel_id))
        if not isinstance(channel, discord.TextChannel):
            raise TypeError(f"Channel {channel_id} is not a Discord text channel")
        return channel

    async def _get_thread(self, thread_id: str) -> discord.Thread:
        client = self._require_client()
        channel = client.get_channel(int(thread_id))
        if channel is None:
            channel = await client.fetch_channel(int(thread_id))
        if not isinstance(channel, discord.Thread):
            raise TypeError(f"Channel {thread_id} is not a Discord thread")
        return channel

    async def _get_or_create_webhook(
        self, *, guild_id: str, hub_channel_id: str
    ) -> discord.Webhook | None:
        key = (guild_id, hub_channel_id)
        cached = self._webhook_cache.get(key)
        if cached is not None:
            return cached

        channel = await self._get_text_channel(hub_channel_id)
        try:
            hooks = await channel.webhooks()
        except Exception:
            self._logger.info("webhook fetch failed hub_channel_id=%s", hub_channel_id)
            return None

        webhook = next(
            (hook for hook in hooks if hook.name == self._webhook_name), None
        )
        if webhook is None:
            try:
                webhook = await channel.create_webhook(name=self._webhook_name)
            except Exception:
                self._logger.info(
                    "webhook create failed hub_channel_id=%s", hub_channel_id
                )
                return None

        self._webhook_cache[key] = webhook
        return webhook
