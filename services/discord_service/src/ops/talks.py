from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from bt_store.engine import get_session_factory, init_database
from bt_store.models_core import Agent, Room, RoomMember
from sqlalchemy import select


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
        rooms = (
            (
                await session.execute(
                    select(Room)
                    .join(RoomMember, RoomMember.room_pk == Room.room_pk)
                    .where(
                        Room.platform == "discord",
                        Room.kind == "dialogue",
                        RoomMember.platform == "discord",
                        RoomMember.platform_user_id == owner_discord_user_id,
                        RoomMember.role == "owner",
                    )
                    .order_by(Room.last_activity_at.desc())
                    .limit(max_rows)
                )
            )
            .scalars()
            .all()
        )

        rows: list[TalkRow] = []
        for room in rooms:
            meta = dict(room.meta_json or {})
            guild_id = str(meta.get("guild_id") or "")
            participants = (
                await session.execute(
                    select(Agent, RoomMember)
                    .join(RoomMember, RoomMember.agent_id == Agent.agent_id)
                    .where(RoomMember.room_pk == room.room_pk)
                    .order_by(RoomMember.display_order)
                )
            ).all()
            rows.append(
                TalkRow(
                    talk_id=str(room.room_pk),
                    guild_id=guild_id,
                    thread_id=room.room_id,
                    status=room.status,
                    participant_slugs=[agent.slug for agent, _ in participants],
                    participant_names=[agent.display_name for agent, _ in participants],
                    last_activity_at=room.last_activity_at,
                )
            )
        return rows


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
                select(Room).where(
                    Room.platform == "discord",
                    Room.kind == "dialogue",
                    Room.room_id == thread_id,
                    Room.status == "open",
                )
            )
        ).scalar_one_or_none()
        if row is None:
            return False
        row.status = "closed"
        await session.commit()
        return True
