from uuid import uuid4

from bt_common.citation import Citation
from bt_common.matrix_helpers import format_ghost_response


def test_ghost_response_event_schema() -> None:
    citation = Citation(
        index=1,
        segment_id=uuid4(),
        emos_message_id="a:b:c:seg:1",
        source_title="The Analects",
        source_url="https://example.com/source",
        quote="Learning without thought is labor lost.",
        platform="gutenberg",
    )

    payload = format_ghost_response(
        "Learning without thought is labor lost.",
        [citation],
    )

    assert payload["msgtype"] == "m.text"
    assert "[^1]" in payload["body"]
    assert "<sup>[1]</sup>" in payload["formatted_body"]
    ext = payload["com.bibliotalk.citations"]
    assert ext["version"] == "1"
    assert len(ext["items"]) == 1
