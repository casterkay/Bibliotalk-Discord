from datetime import datetime, timezone
from uuid import uuid4

from bt_common.citation import Citation, Evidence, SegmentLike, validate_citations


def test_valid_citation_passes() -> None:
    agent_id = uuid4()
    segment_id = uuid4()
    citation = Citation(
        index=1,
        segment_id=segment_id,
        emos_message_id="a:b:c:seg:1",
        source_title="Source",
        source_url="https://example.com",
        quote="learning without thought",
        platform="gutenberg",
        timestamp=datetime.now(tz=timezone.utc),
    )
    segments = [SegmentLike(id=segment_id, agent_id=agent_id, text="learning without thought is labor lost")]

    validated = validate_citations([citation], segments, responding_agent_id=agent_id)

    assert validated == [citation]


def test_citation_with_nonexistent_segment_id_is_stripped() -> None:
    agent_id = uuid4()
    citation = Citation(
        index=1,
        segment_id=uuid4(),
        emos_message_id="a:b:c:seg:1",
        source_title="Source",
        source_url="https://example.com",
        quote="quote",
        platform="gutenberg",
    )

    validated = validate_citations([citation], [], responding_agent_id=agent_id)

    assert validated == []


def test_citation_with_mismatched_quote_is_stripped() -> None:
    agent_id = uuid4()
    segment_id = uuid4()
    citation = Citation(
        index=1,
        segment_id=segment_id,
        emos_message_id="a:b:c:seg:1",
        source_title="Source",
        source_url="https://example.com",
        quote="missing quote",
        platform="gutenberg",
    )
    segments = [SegmentLike(id=segment_id, agent_id=agent_id, text="real segment text")]

    validated = validate_citations([citation], segments, responding_agent_id=agent_id)

    assert validated == []


def test_cross_agent_citation_is_rejected() -> None:
    responding_agent_id = uuid4()
    other_agent_id = uuid4()
    segment_id = uuid4()
    citation = Citation(
        index=1,
        segment_id=segment_id,
        emos_message_id="a:b:c:seg:1",
        source_title="Source",
        source_url="https://example.com",
        quote="real",
        platform="gutenberg",
    )
    segments = [SegmentLike(id=segment_id, agent_id=other_agent_id, text="real quote")]

    validated = validate_citations([citation], segments, responding_agent_id=responding_agent_id)

    assert validated == []


def test_evidence_to_citation_conversion() -> None:
    evidence = Evidence(
        segment_id=uuid4(),
        emos_message_id="a:b:c:seg:1",
        source_title="Analects",
        source_url="https://example.com",
        text="learning without thought",
        platform="gutenberg",
    )

    citation = Citation.from_evidence(evidence, index=1, quote="learning")

    assert citation.index == 1
    assert citation.segment_id == evidence.segment_id
    assert citation.quote == "learning"
