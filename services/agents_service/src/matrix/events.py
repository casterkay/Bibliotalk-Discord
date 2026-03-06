"""Typed Matrix event contracts for agents_service.

Constitution principle III requires Matrix event schemas to be defined as typed
models, not ad-hoc dict manipulation.
"""

from __future__ import annotations

from typing import Literal, TypeAlias

from pydantic import BaseModel, ConfigDict, Field, JsonValue, field_validator

JSONValue: TypeAlias = JsonValue


class MatrixRelatesTo(BaseModel):
    model_config = ConfigDict(extra="allow")

    rel_type: str | None = Field(default=None, alias="rel_type")
    event_id: str | None = None


class MatrixMentions(BaseModel):
    model_config = ConfigDict(extra="allow")

    user_ids: list[str] = Field(default_factory=list)


class MatrixMessageContent(BaseModel):
    model_config = ConfigDict(extra="allow", populate_by_name=True)

    msgtype: str | None = None
    body: str | None = None
    relates_to: MatrixRelatesTo | None = Field(default=None, alias="m.relates_to")
    mentions: MatrixMentions | None = Field(default=None, alias="m.mentions")


class MatrixMemberContent(BaseModel):
    model_config = ConfigDict(extra="allow")

    membership: str | None = None


class MatrixEventBase(BaseModel):
    model_config = ConfigDict(extra="allow")

    type: str | None = None
    room_id: str | None = None
    sender: str | None = None
    event_id: str | None = None


class RoomMessageEvent(MatrixEventBase):
    type: Literal["m.room.message"]
    content: MatrixMessageContent = Field(default_factory=MatrixMessageContent)


class RoomMemberEvent(MatrixEventBase):
    type: Literal["m.room.member"]
    state_key: str | None = None
    content: MatrixMemberContent = Field(default_factory=MatrixMemberContent)


class UnknownMatrixEvent(MatrixEventBase):
    """A best-effort wrapper for events we don't currently model."""

    type: str | None = None
    raw: dict[str, JSONValue] = Field(default_factory=dict)


MatrixEvent: TypeAlias = RoomMessageEvent | RoomMemberEvent | UnknownMatrixEvent


def _to_json_value(value: object) -> JSONValue | None:
    if isinstance(value, (str, int, float, bool)) or value is None:
        return value
    if isinstance(value, list):
        out: list[JSONValue] = []
        for item in value:
            converted = _to_json_value(item)
            if converted is not None:
                out.append(converted)
        return out
    if isinstance(value, dict):
        out: dict[str, JSONValue] = {}
        for k, v in value.items():
            converted = _to_json_value(v)
            if converted is not None:
                out[str(k)] = converted
        return out
    return None


def parse_matrix_event(value: object) -> MatrixEvent:
    if not isinstance(value, dict):
        return UnknownMatrixEvent(raw={})

    event_type = value.get("type")
    if event_type == "m.room.message":
        return RoomMessageEvent.model_validate(value)
    if event_type == "m.room.member":
        return RoomMemberEvent.model_validate(value)

    # Preserve the raw payload for debugging/forward-compat.
    raw: dict[str, JSONValue] = {}
    for k, v in value.items():
        converted = _to_json_value(v)
        if converted is not None:
            raw[str(k)] = converted
    return UnknownMatrixEvent(
        type=str(event_type) if event_type is not None else None,
        room_id=str(value.get("room_id")) if value.get("room_id") is not None else None,
        sender=str(value.get("sender")) if value.get("sender") is not None else None,
        event_id=str(value.get("event_id")) if value.get("event_id") is not None else None,
        raw=raw,
    )


class AppserviceTransaction(BaseModel):
    model_config = ConfigDict(extra="allow")

    events: list[MatrixEvent] = Field(default_factory=list)

    @field_validator("events", mode="before")
    @classmethod
    def _parse_events(cls, v: object) -> list[MatrixEvent]:
        if v is None:
            return []
        if not isinstance(v, list):
            raise TypeError("events must be a list")
        return [parse_matrix_event(item) for item in v]
