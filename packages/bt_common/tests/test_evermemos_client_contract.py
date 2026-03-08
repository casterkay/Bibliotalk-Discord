from __future__ import annotations

import pytest
from bt_common.evermemos_client import EverMemOSClient


class FakeConversationMeta:
    def __init__(self) -> None:
        self.create_calls: list[dict] = []
        self.create_results: list = []

    async def create(self, **kwargs):
        self.create_calls.append(kwargs)
        value = self.create_results.pop(0)
        if isinstance(value, Exception):
            raise value
        return value


class FakeMemories:
    def __init__(self) -> None:
        self.add_calls: list[dict] = []
        self.delete_calls: list[dict] = []
        self.add_results: list = []
        self.delete_results: list = []
        self.conversation_meta = FakeConversationMeta()

    async def add(self, **kwargs):
        self.add_calls.append(kwargs)
        value = self.add_results.pop(0)
        if isinstance(value, Exception):
            raise value
        return value

    async def delete(self, **kwargs):
        self.delete_calls.append(kwargs)
        value = self.delete_results.pop(0)
        if isinstance(value, Exception):
            raise value
        return value


class FakeSDK:
    def __init__(self, memories: FakeMemories):
        self.v0 = type("V0", (), {})()
        self.v0.memories = memories

    async def close(self):
        return None


@pytest.mark.anyio
async def test_memorize_contract_uses_stable_ids_and_create_time() -> None:
    memories = FakeMemories()
    memories.add_results = [{"status": "ok", "result": {"status_info": "extracted"}}]
    client = EverMemOSClient("https://emos.local", api_key="secret", sdk_client=FakeSDK(memories))

    await client.memorize(
        {
            "message_id": "alan-watts:youtube:abc123:seg:2",
            "sender": "alan-watts",
            "content": "Transcript segment",
            "create_time": "2026-03-07T12:30:45+00:00",
            "group_id": "alan-watts:youtube:abc123",
            "group_name": "Alan Watts Lecture",
            "role": "assistant",
        }
    )

    call = memories.add_calls[-1]
    assert call["message_id"] == "alan-watts:youtube:abc123:seg:2"
    assert call["create_time"] == "2026-03-07T12:30:45+00:00"
    assert call["group_id"] == "alan-watts:youtube:abc123"


@pytest.mark.anyio
async def test_save_conversation_meta_contract_uses_group_id() -> None:
    memories = FakeMemories()
    memories.conversation_meta.create_results = [
        {"status": "ok", "result": {"group_id": "alan-watts:youtube:abc123"}}
    ]
    client = EverMemOSClient("https://emos.local", sdk_client=FakeSDK(memories))

    await client.save_conversation_meta(
        group_id="alan-watts:youtube:abc123",
        source_meta={
            "title": "Alan Watts Lecture",
            "source_url": "https://www.youtube.com/watch?v=abc123",
            "channel_name": "Alan Watts Org",
        },
    )

    call = memories.conversation_meta.create_calls[-1]
    assert call["extra_body"]["group_id"] == "alan-watts:youtube:abc123"
    assert call["extra_body"]["source_meta"]["channel_name"] == "Alan Watts Org"


@pytest.mark.anyio
async def test_delete_by_group_id_contract_targets_single_video() -> None:
    memories = FakeMemories()
    memories.delete_results = [{"status": "ok", "result": {"count": 4}}]
    client = EverMemOSClient("https://emos.local", api_key="secret", sdk_client=FakeSDK(memories))

    result = await client.delete_by_group_id("alan-watts:youtube:abc123")

    assert result["result"]["count"] == 4
    call = memories.delete_calls[-1]
    assert call["group_id"] == "alan-watts:youtube:abc123"
    assert call["extra_headers"]["Authorization"] == "Bearer secret"
