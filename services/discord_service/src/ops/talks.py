from __future__ import annotations

import uuid
from dataclasses import dataclass
from datetime import datetime

from bt_common.evidence_store.engine import get_session_factory, init_database
from bt_common.evidence_store.models import Figure, TalkParticipant, TalkThread
from sqlalchemy import select, update


@dataclass(frozen=True, slots=True)
class TalkRow:
    talk_id: str
    guild_id: str
    thread_id: str
    status: str
    participant_slugs: list[str]
    participant_names: list[str]
    last_activity_at: datetime

    def thread_url(self) -> str:
        return f"https://discord.com/channels/{self.guild_id}/{self.thread_id}"


async def list_talks(
    *,
    db_path: str | None,
    owner_discord_user_id: str,
    limit: int = 10,
) -> list[TalkRow]:
    await init_database(db_path)
    session_factory = get_session_factory(db_path)
    max_rows = max(1, int(limit))
    async with session_factory() as session:
        talk_ids = (
            (
                await session.execute(
                    select(TalkThread.talk_id)
                    .where(TalkThread.owner_discord_user_id == owner_discord_user_id)
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
                .join(TalkParticipant, TalkParticipant.talk_id == TalkThread.talk_id)
                .join(Figure, Figure.figure_id == TalkParticipant.figure_id)
                .where(TalkThread.talk_id.in_(talk_ids))
                .order_by(
                    TalkThread.last_activity_at.desc(), TalkParticipant.display_order
                )
            )
        ).all()

    grouped: dict[uuid.UUID, TalkRow] = {}
    for talk, participant, figure in rows:
        entry = grouped.get(talk.talk_id)
        if entry is None:
            entry = TalkRow(
                talk_id=str(talk.talk_id),
                guild_id=talk.guild_id,
                thread_id=talk.thread_id,
                status=talk.status,
                participant_slugs=[],
                participant_names=[],
                last_activity_at=talk.last_activity_at,
            )
            grouped[talk.talk_id] = entry
        entry.participant_slugs.append(figure.emos_user_id)
        entry.participant_names.append(figure.display_name)

    ordered = sorted(grouped.values(), key=lambda e: e.last_activity_at, reverse=True)
    return ordered[:max_rows]


async def close_talk_by_thread_id(
    *,
    db_path: str | None,
    thread_id: str,
) -> bool:
    await init_database(db_path)
    session_factory = get_session_factory(db_path)
    async with session_factory() as session:
        row = (
            await session.execute(
                select(TalkThread).where(
                    TalkThread.thread_id == thread_id,
                    TalkThread.status == "open",
                )
            )
        ).scalar_one_or_none()
        if row is None:
            return False
        await session.execute(
            update(TalkThread)
            .where(TalkThread.talk_id == row.talk_id)
            .values(status="closed")
        )
        await session.commit()
        return True
