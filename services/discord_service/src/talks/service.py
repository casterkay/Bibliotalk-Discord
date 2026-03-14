from __future__ import annotations

import asyncio
import logging
import re
import uuid
from dataclasses import dataclass
from datetime import UTC, datetime

from agents_service.agent.orchestrator import DMContext, DMOrchestrator
from agents_service.models.citation import (
    NO_EVIDENCE_RESPONSE,
    extract_memory_links,
    validate_evidence_links,
)
from bt_common.evidence_store.models import (
    DiscordUserSettings,
    Figure,
    TalkParticipant,
    TalkThread,
)
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from .directory import FigureDirectory, FigureInfo
from .router import FacilitatorRouter
from .transport import EligibleGuild, TalkTransport

logger = logging.getLogger("discord_service")

_SENTENCE_SPLIT_RE = re.compile(r"(?<=[.!?])\s+")


def _utc_now() -> datetime:
    return datetime.now(tz=UTC)


@dataclass(frozen=True, slots=True)
class TalkStartResult:
    kind: str  # created|resumed|choose_guild|error
    message: str
    talk_id: uuid.UUID | None = None
    guild_id: str | None = None
    thread_id: str | None = None
    participant_slugs: list[str] | None = None
    eligible_guilds: list[EligibleGuild] | None = None

    def thread_url(self) -> str | None:
        if not self.guild_id or not self.thread_id:
            return None
        return f"https://discord.com/channels/{self.guild_id}/{self.thread_id}"


@dataclass(frozen=True, slots=True)
class TalkListEntry:
    talk_id: uuid.UUID
    guild_id: str
    thread_id: str
    status: str
    participant_slugs: list[str]
    participant_names: list[str]
    last_activity_at: datetime

    def thread_url(self) -> str:
        return f"https://discord.com/channels/{self.guild_id}/{self.thread_id}"


class TalkService:
    def __init__(
        self,
        *,
        session_factory: async_sessionmaker[AsyncSession],
        figure_directory: FigureDirectory,
        router: FacilitatorRouter,
        orchestrator: DMOrchestrator,
        transport: TalkTransport,
        hub_channel_name: str,
        logger_: logging.Logger | None = None,
        max_participants: int = 6,
    ) -> None:
        self._session_factory = session_factory
        self._directory = figure_directory
        self._router = router
        self._orchestrator = orchestrator
        self._transport = transport
        self._hub_channel_name = hub_channel_name
        self._logger = logger_ or logger
        self._max_participants = max(1, max_participants)
        self._thread_locks: dict[str, asyncio.Lock] = {}

    async def start_talk(
        self,
        *,
        owner_discord_user_id: str,
        characters: str,
        guild_id: str | None = None,
    ) -> TalkStartResult:
        participants = self._parse_participants(characters)
        if not participants:
            return TalkStartResult(
                kind="error",
                message="No characters specified. Try `/talk Alan Watts, Naval`.",
            )
        if len(participants) > self._max_participants:
            return TalkStartResult(
                kind="error",
                message=f"Too many characters. Max is {self._max_participants}.",
            )

        resolved: list[FigureInfo] = []
        for token in participants:
            info = self._directory.resolve_token(token)
            if info is None:
                available = ", ".join(
                    sorted({f.display_name for f in self._directory.list_figures()})
                )
                return TalkStartResult(
                    kind="error",
                    message=f"Unknown character: `{token}`. Available: {available}",
                )
            if info.figure_id not in {item.figure_id for item in resolved}:
                resolved.append(info)

        chosen_guild = await self._resolve_guild_id(
            owner_discord_user_id=owner_discord_user_id,
            explicit_guild_id=guild_id,
        )
        if isinstance(chosen_guild, list):
            if len(chosen_guild) == 1:
                chosen_guild_id = chosen_guild[0].guild_id
            else:
                return TalkStartResult(
                    kind="choose_guild",
                    message="Choose which server should host this talk:",
                    eligible_guilds=chosen_guild,
                    participant_slugs=[f.figure_slug for f in resolved],
                )
        else:
            chosen_guild_id = chosen_guild

        try:
            hub_channel_id = await self._transport.resolve_hub_channel_id(
                guild_id=chosen_guild_id,
                hub_channel_name=self._hub_channel_name,
            )
        except Exception as exc:
            self._logger.info(
                "hub channel resolution failed guild_id=%s err=%s",
                chosen_guild_id,
                type(exc).__name__,
            )
            # Default guild might be stale; force re-pick.
            guilds = await self._transport.list_eligible_guilds(
                hub_channel_name=self._hub_channel_name
            )
            if not guilds:
                return TalkStartResult(
                    kind="error",
                    message=(
                        "I couldn't find any server with a `#bibliotalk` channel where I can create private threads."
                    ),
                    participant_slugs=[f.figure_slug for f in resolved],
                )
            return TalkStartResult(
                kind="choose_guild",
                message="Choose which server should host this talk:",
                eligible_guilds=guilds,
                participant_slugs=[f.figure_slug for f in resolved],
            )

        async with self._session_factory() as session:
            existing = await self._find_existing_open_talk(
                session,
                owner_discord_user_id=owner_discord_user_id,
                guild_id=chosen_guild_id,
                participant_ids={p.figure_id for p in resolved},
            )
            if existing is not None:
                if await self._transport.thread_exists(thread_id=existing.thread_id):
                    existing.last_activity_at = _utc_now()
                    await session.commit()
                    await self._upsert_user_default_guild(
                        session,
                        owner_discord_user_id=owner_discord_user_id,
                        guild_id=chosen_guild_id,
                    )
                    await session.commit()
                    try:
                        await self._transport.add_user_to_thread(
                            thread_id=existing.thread_id,
                            discord_user_id=owner_discord_user_id,
                        )
                    except Exception:
                        pass
                    return TalkStartResult(
                        kind="resumed",
                        message="Resumed your existing talk.",
                        talk_id=existing.talk_id,
                        guild_id=existing.guild_id,
                        thread_id=existing.thread_id,
                        participant_slugs=[f.figure_slug for f in resolved],
                    )

                existing.status = "closed"
                await session.commit()

        thread_name = self._build_thread_name(resolved)
        thread_id = await self._transport.create_private_thread(
            hub_channel_id=hub_channel_id,
            name=thread_name,
            auto_archive_duration_minutes=10080,  # 7 days
            invitable=False,
        )
        await self._transport.add_user_to_thread(
            thread_id=thread_id,
            discord_user_id=owner_discord_user_id,
        )

        roster_message_id = await self._transport.send_bot_message(
            thread_id=thread_id,
            content=self._build_roster_message(resolved),
        )
        try:
            await self._transport.pin_message(
                thread_id=thread_id, message_id=roster_message_id
            )
        except Exception:
            pass

        talk_id = uuid.uuid4()
        async with self._session_factory() as session:
            session.add(
                TalkThread(
                    talk_id=talk_id,
                    owner_discord_user_id=owner_discord_user_id,
                    guild_id=chosen_guild_id,
                    hub_channel_id=hub_channel_id,
                    thread_id=thread_id,
                    status="open",
                    created_at=_utc_now(),
                    last_activity_at=_utc_now(),
                )
            )
            for idx, info in enumerate(resolved):
                session.add(
                    TalkParticipant(
                        talk_id=talk_id,
                        figure_id=info.figure_id,
                        display_order=idx,
                    )
                )
            await self._upsert_user_default_guild(
                session,
                owner_discord_user_id=owner_discord_user_id,
                guild_id=chosen_guild_id,
            )
            await session.commit()

        return TalkStartResult(
            kind="created",
            message="Created a new talk thread.",
            talk_id=talk_id,
            guild_id=chosen_guild_id,
            thread_id=thread_id,
            participant_slugs=[f.figure_slug for f in resolved],
        )

    async def list_talks(
        self, *, owner_discord_user_id: str, limit: int = 10
    ) -> list[TalkListEntry]:
        max_rows = max(1, limit)
        async with self._session_factory() as session:
            talk_ids = (
                (
                    await session.execute(
                        select(TalkThread.talk_id)
                        .where(
                            TalkThread.owner_discord_user_id == owner_discord_user_id
                        )
                        .order_by(TalkThread.last_activity_at.desc())
                        .limit(max_rows)
                    )
                )
                .scalars()
                .all()
            )
            if not talk_ids:
                return []

            rows = (
                await session.execute(
                    select(TalkThread, TalkParticipant, Figure)
                    .join(
                        TalkParticipant, TalkParticipant.talk_id == TalkThread.talk_id
                    )
                    .join(Figure, Figure.figure_id == TalkParticipant.figure_id)
                    .where(TalkThread.talk_id.in_(talk_ids))
                    .order_by(
                        TalkThread.last_activity_at.desc(),
                        TalkParticipant.display_order,
                    )
                )
            ).all()

        grouped: dict[uuid.UUID, TalkListEntry] = {}
        for talk, participant, figure in rows:
            entry = grouped.get(talk.talk_id)
            if entry is None:
                grouped[talk.talk_id] = TalkListEntry(
                    talk_id=talk.talk_id,
                    guild_id=talk.guild_id,
                    thread_id=talk.thread_id,
                    status=talk.status,
                    participant_slugs=[],
                    participant_names=[],
                    last_activity_at=talk.last_activity_at,
                )
                entry = grouped[talk.talk_id]
            entry.participant_slugs.append(figure.emos_user_id)
            entry.participant_names.append(figure.display_name)

        ordered = sorted(
            grouped.values(), key=lambda e: e.last_activity_at, reverse=True
        )
        return ordered[:max_rows]

    async def handle_thread_message(
        self,
        *,
        guild_id: str,
        thread_id: str,
        author_discord_user_id: str,
        content: str,
    ) -> bool:
        talk = await self._get_open_talk_by_thread_id(thread_id)
        if talk is None:
            return False

        lock = self._thread_locks.setdefault(thread_id, asyncio.Lock())
        async with lock:
            talk = await self._get_open_talk_by_thread_id(thread_id)
            if talk is None:
                return False

            participants = await self._get_talk_participants(talk.talk_id)
            if not participants:
                await self._transport.send_bot_message(
                    thread_id=thread_id,
                    content="This talk has no participants configured.",
                )
                return True

            override_token = self._directory.resolve_override_prefix(content)
            speaker_infos: list[FigureInfo] = []
            effective_content = content
            if override_token:
                override_info = self._directory.resolve_token(override_token)
                if override_info and override_info.figure_id in {
                    p.figure_id for p in participants
                }:
                    speaker_infos = [override_info]
                    effective_content = content.lstrip()[
                        len(override_token) + 1 :
                    ].lstrip()
                    if not effective_content:
                        effective_content = content

            last_slug = None
            if talk.last_routed_figure_id:
                last_info = self._directory.get_by_id(talk.last_routed_figure_id)
                last_slug = last_info.figure_slug if last_info else None

            if not speaker_infos:
                decision = await self._router.route(
                    message=content,
                    participants=participants,
                    last_speaker_slug=last_slug,
                )
                if decision is not None:
                    speaker_infos = [
                        info
                        for info in participants
                        if info.figure_slug in set(decision.speaker_slugs)
                    ]
                    if decision.facilitator_note:
                        await self._transport.send_bot_message(
                            thread_id=thread_id, content=decision.facilitator_note
                        )

            if not speaker_infos:
                speaker_infos = [self._pick_next_speaker(participants, last_slug)]

            for speaker in speaker_infos:
                await self._respond_as_character(
                    guild_id=guild_id,
                    hub_channel_id=talk.hub_channel_id,
                    thread_id=thread_id,
                    author_discord_user_id=author_discord_user_id,
                    speaker=speaker,
                    content=effective_content,
                )

            async with self._session_factory() as session:
                await session.execute(
                    update(TalkThread)
                    .where(TalkThread.talk_id == talk.talk_id)
                    .values(
                        last_activity_at=_utc_now(),
                        last_routed_figure_id=speaker_infos[-1].figure_id,
                    )
                )
                await session.commit()

        return True

    def _parse_participants(self, characters: str) -> list[str]:
        raw = (characters or "").strip()
        if not raw:
            return []
        return [item.strip() for item in raw.split(",") if item.strip()]

    async def _resolve_guild_id(
        self, *, owner_discord_user_id: str, explicit_guild_id: str | None
    ) -> str | list[EligibleGuild]:
        if explicit_guild_id:
            return explicit_guild_id

        async with self._session_factory() as session:
            settings = await session.get(DiscordUserSettings, owner_discord_user_id)
            default_guild = (settings.default_guild_id if settings else None) or None

        if default_guild:
            return default_guild

        return await self._transport.list_eligible_guilds(
            hub_channel_name=self._hub_channel_name
        )

    async def _upsert_user_default_guild(
        self, session: AsyncSession, *, owner_discord_user_id: str, guild_id: str
    ) -> None:
        settings = await session.get(DiscordUserSettings, owner_discord_user_id)
        if settings is None:
            session.add(
                DiscordUserSettings(
                    discord_user_id=owner_discord_user_id,
                    default_guild_id=guild_id,
                    created_at=_utc_now(),
                    updated_at=_utc_now(),
                )
            )
            return
        settings.default_guild_id = guild_id
        settings.updated_at = _utc_now()

    async def _find_existing_open_talk(
        self,
        session: AsyncSession,
        *,
        owner_discord_user_id: str,
        guild_id: str,
        participant_ids: set[uuid.UUID],
    ) -> TalkThread | None:
        talks = (
            (
                await session.execute(
                    select(TalkThread)
                    .where(
                        TalkThread.owner_discord_user_id == owner_discord_user_id,
                        TalkThread.guild_id == guild_id,
                        TalkThread.status == "open",
                    )
                    .order_by(TalkThread.last_activity_at.desc())
                )
            )
            .scalars()
            .all()
        )
        if not talks:
            return None

        for talk in talks:
            ids = (
                (
                    await session.execute(
                        select(TalkParticipant.figure_id).where(
                            TalkParticipant.talk_id == talk.talk_id
                        )
                    )
                )
                .scalars()
                .all()
            )
            if set(ids) == participant_ids:
                return talk
        return None

    async def _get_open_talk_by_thread_id(self, thread_id: str) -> TalkThread | None:
        async with self._session_factory() as session:
            return (
                await session.execute(
                    select(TalkThread).where(
                        TalkThread.thread_id == thread_id, TalkThread.status == "open"
                    )
                )
            ).scalar_one_or_none()

    async def _get_talk_participants(self, talk_id: uuid.UUID) -> list[FigureInfo]:
        async with self._session_factory() as session:
            rows = (
                await session.execute(
                    select(Figure, TalkParticipant)
                    .join(
                        TalkParticipant, TalkParticipant.figure_id == Figure.figure_id
                    )
                    .where(TalkParticipant.talk_id == talk_id)
                    .order_by(TalkParticipant.display_order)
                )
            ).all()
        infos: list[FigureInfo] = []
        for figure, _participant in rows:
            info = self._directory.get_by_id(figure.figure_id)
            if info is None:
                info = FigureInfo(
                    figure_id=figure.figure_id,
                    figure_slug=figure.emos_user_id,
                    display_name=figure.display_name,
                    persona_summary=figure.persona_summary,
                )
            infos.append(info)
        return infos

    def _pick_next_speaker(
        self, participants: list[FigureInfo], last_slug: str | None
    ) -> FigureInfo:
        if not participants:
            raise ValueError("participants cannot be empty")
        if not last_slug:
            return participants[0]
        for idx, info in enumerate(participants):
            if info.figure_slug == last_slug:
                return participants[(idx + 1) % len(participants)]
        return participants[0]

    async def _respond_as_character(
        self,
        *,
        guild_id: str,
        hub_channel_id: str,
        thread_id: str,
        author_discord_user_id: str,
        speaker: FigureInfo,
        content: str,
    ) -> None:
        result = await self._orchestrator.run(
            DMContext(
                figure_id=speaker.figure_id,
                figure_slug=speaker.figure_slug,
                discord_user_id=author_discord_user_id,
                discord_channel_id=thread_id,
                content=content,
            )
        )
        validated_text = validate_evidence_links(
            result.response_text,
            list(result.evidence),
            figure_emos_user_id=speaker.figure_slug,
        )
        if not extract_memory_links(validated_text):
            validated_text = NO_EVIDENCE_RESPONSE

        for chunk in _split_response_text(validated_text):
            await self._transport.send_persona_message(
                guild_id=guild_id,
                hub_channel_id=hub_channel_id,
                thread_id=thread_id,
                persona_name=speaker.display_name,
                content=chunk,
            )

    def _build_thread_name(self, participants: list[FigureInfo]) -> str:
        date = _utc_now().strftime("%Y-%m-%d")
        names = " + ".join(p.display_name for p in participants[:3])
        if len(participants) > 3:
            names = f"{names} +{len(participants) - 3}"
        return f"talk: {names} — {date}"[:100]

    def _build_roster_message(self, participants: list[FigureInfo]) -> str:
        roster = "\n".join(
            f"- {p.display_name} (`@{p.figure_slug}`)" for p in participants
        )
        return (
            "Welcome to your private Bibliotalk thread.\n\n"
            "**Participants**\n"
            f"{roster}\n\n"
            "**How it works**\n"
            "- Just send messages normally.\n"
            "- I route each message to the most relevant character(s).\n"
            "- Override routing by starting a message with `@slug` (e.g. `@alan-watts ...`).\n"
        ).strip()[:2000]


def _split_response_text(text: str, *, limit: int = 2000) -> list[str]:
    compact = " ".join((text or "").split())
    if len(compact) <= limit:
        return [compact]
    sentences = _SENTENCE_SPLIT_RE.split(compact)
    chunks: list[str] = []
    current = ""
    for sentence in sentences:
        candidate = sentence.strip()
        if not candidate:
            continue
        merged = f"{current} {candidate}".strip()
        if current and len(merged) > limit:
            chunks.append(current)
            current = candidate
            continue
        if len(candidate) > limit:
            if current:
                chunks.append(current)
            current = candidate[:limit]
            continue
        current = merged
    if current:
        chunks.append(current)
    return chunks or [compact[:limit]]
