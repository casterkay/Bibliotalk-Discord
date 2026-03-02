from __future__ import annotations


def build_group_id(*, user_id: str, platform: str, external_id: str) -> str:
    return f"{user_id}:{platform}:{external_id}"


def build_message_id(*, user_id: str, platform: str, external_id: str, seq: int) -> str:
    return f"{user_id}:{platform}:{external_id}:seg:{seq}"

