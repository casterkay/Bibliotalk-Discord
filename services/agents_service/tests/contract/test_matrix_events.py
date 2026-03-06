from __future__ import annotations

from uuid import uuid4

from agents_service.matrix.appservice import format_ghost_response
from agents_service.matrix.events import AppserviceTransaction
from agents_service.models.citation import Citation


def test_appservice_transaction_parses_supported_event_types() -> None:
    ghost_user_id = "@bt_ghost_confucius:example"
    payload = {
        "events": [
            {
                "type": "m.room.message",
                "room_id": "!room:example",
                "sender": "@alice:example",
                "event_id": "$m1",
                "content": {"msgtype": "m.text", "body": f"hi {ghost_user_id}"},
            },
            {
                "type": "m.room.member",
                "room_id": "!room:example",
                "sender": "@alice:example",
                "state_key": ghost_user_id,
                "content": {"membership": "invite"},
            },
            {
                "type": "m.room.topic",
                "room_id": "!room:example",
                "sender": "@alice:example",
                "content": {"topic": "ignored"},
            },
        ]
    }

    txn = AppserviceTransaction.model_validate(payload)
    assert len(txn.events) == 3
    assert txn.events[0].type == "m.room.message"
    assert txn.events[1].type == "m.room.member"
    assert txn.events[2].type == "m.room.topic"


def test_ghost_message_payload_includes_citation_extension() -> None:
    citation = Citation(
        index=1,
        segment_id=uuid4(),
        emos_message_id="a:b:c:seg:1",
        source_title="The Analects",
        source_url="https://example.com",
        quote="Learning without thought is labor lost.",
        platform="gutenberg",
    )

    payload = format_ghost_response("Answer [^1]", [citation])
    ext = payload.get("com.bibliotalk.citations")
    assert isinstance(ext, dict)
    assert ext.get("version") == "1"
    items = ext.get("items")
    assert isinstance(items, list) and items and items[0]["index"] == 1
