from __future__ import annotations

import pytest
from bt_common.evermemos_client import EverMemOSClient
from bt_common.exceptions import EMOSNotFoundError


class FakeStatusError(Exception):
    def __init__(
        self, status_code: int, body: dict | None = None, message: str = "error"
    ):
        super().__init__(message)
        self.status_code = status_code
        self.body = body or {}
        self.message = message


class FakeModel:
    def __init__(self, payload: dict):
        self._payload = payload

    def to_dict(self) -> dict:
        return self._payload


class FakeConversationMeta:
    def __init__(self):
        self.get_results: list = []
        self.create_results: list = []

    async def get(self, **kwargs):
        value = self.get_results.pop(0)
        if isinstance(value, Exception):
            raise value
        return value

    async def create(self, **kwargs):
        value = self.create_results.pop(0)
        if isinstance(value, Exception):
            raise value
        return value


class FakeMemories:
    def __init__(self):
        self.add_results: list = []
        self.search_results: list = []
        self.conversation_meta = FakeConversationMeta()

    async def add(self, **kwargs):
        value = self.add_results.pop(0)
        if isinstance(value, Exception):
            raise value
        return value

    async def search(self, **kwargs):
        value = self.search_results.pop(0)
        if isinstance(value, Exception):
            raise value
        return value


class FakeSDK:
    def __init__(self, memories: FakeMemories):
        self.v0 = type("V0", (), {})()
        self.v0.memories = memories

    async def close(self):
        return None


@pytest.mark.asyncio
async def test_parse_memorize_response_shape() -> None:
    memories = FakeMemories()
    memories.add_results = [
        FakeModel(
            {
                "status": "ok",
                "message": "saved",
                "result": {
                    "saved_memories": [],
                    "count": 0,
                    "status_info": "extracted",
                },
            }
        )
    ]
    client = EverMemOSClient("https://emos.local", sdk_client=FakeSDK(memories))

    payload = {"message_id": "msg", "sender": "agent", "content": "segment"}
    result = await client.memorize(payload)

    assert result["result"]["status_info"] in {"extracted", "accumulated"}


@pytest.mark.asyncio
async def test_parse_search_nested_memory_types() -> None:
    memories = FakeMemories()
    memories.search_results = [
        {
            "status": "ok",
            "result": {
                "memories": [
                    {
                        "episodic_memory": [
                            {
                                "summary": "virtue",
                                "group_id": "g1",
                                "importance_score": 0.85,
                            }
                        ]
                    }
                ],
                "total_count": 1,
                "has_more": False,
            },
        }
    ]
    client = EverMemOSClient("https://emos.local", sdk_client=FakeSDK(memories))

    result = await client.search("virtue", user_id="agent")

    memories_payload = result["result"]["memories"]
    assert memories_payload[0]["episodic_memory"][0]["group_id"] == "g1"


@pytest.mark.asyncio
async def test_parse_conversation_meta_response() -> None:
    memories = FakeMemories()
    memories.conversation_meta.get_results = [
        {"status": "ok", "result": {"group_id": "g1", "name": "Episode"}}
    ]
    client = EverMemOSClient("https://emos.local", sdk_client=FakeSDK(memories))

    result = await client.get_conversation_meta("g1")

    assert result["result"]["group_id"] == "g1"


@pytest.mark.asyncio
async def test_parse_error_envelope() -> None:
    memories = FakeMemories()
    memories.conversation_meta.get_results = [
        FakeStatusError(
            404,
            {
                "status": "failed",
                "code": "RESOURCE_NOT_FOUND",
                "message": "missing",
                "timestamp": "2025-01-15T10:30:00+00:00",
                "path": "/api/v0/memories/conversation-meta",
            },
        )
    ]
    client = EverMemOSClient("https://emos.local", sdk_client=FakeSDK(memories))

    with pytest.raises(EMOSNotFoundError):
        await client.get_conversation_meta("missing")
