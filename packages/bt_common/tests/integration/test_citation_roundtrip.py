from __future__ import annotations

from uuid import uuid4

from bt_common.citation import Citation, Evidence, SegmentLike, validate_citations


def test_citation_round_trip_integrity() -> None:
    agent_id = uuid4()
    segment_id = uuid4()

    evidence = Evidence(
        segment_id=segment_id,
        emos_message_id="a:b:c:seg:1",
        source_title="The Analects",
        source_url="https://example.com",
        text="Learning without thought is labor lost.",
        platform="gutenberg",
    )
    citation = Citation.from_evidence(evidence, index=1, quote="Learning without thought")

    segment = SegmentLike(
        id=segment_id,
        agent_id=agent_id,
        text="Learning without thought is labor lost.",
    )

    validated = validate_citations([citation], [segment], responding_agent_id=agent_id)

    assert len(validated) == 1
    assert validated[0].segment_id == segment_id
