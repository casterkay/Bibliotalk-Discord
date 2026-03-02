from uuid import uuid4

from bt_common.segment import Segment, Source, bm25_rerank


def _segment(text: str) -> Segment:
    return Segment(
        id=uuid4(),
        source_id=uuid4(),
        agent_id=uuid4(),
        platform="gutenberg",
        seq=1,
        text=text,
        sha256="deadbeef",
        emos_message_id="a:b:c:seg:1",
    )


def test_segment_model_creation() -> None:
    segment = _segment("Virtue and learning")
    assert segment.text == "Virtue and learning"


def test_bm25_scoring_returns_relevant_segments_first() -> None:
    segments = [
        _segment("On governance and benevolence"),
        _segment("Learning and reflection are essential for wisdom"),
        _segment("Music and rituals in harmony"),
    ]

    ranked = bm25_rerank("learning reflection wisdom", segments, top_k=2)

    assert len(ranked) == 2
    assert "Learning and reflection" in ranked[0].text


def test_bm25_with_empty_query() -> None:
    segments = [_segment("a"), _segment("b")]

    ranked = bm25_rerank("", segments, top_k=1)

    assert len(ranked) == 1
    assert ranked[0].text == "a"


def test_top_k_limiting() -> None:
    segments = [_segment("a"), _segment("b"), _segment("c")]

    ranked = bm25_rerank("a", segments, top_k=2)

    assert len(ranked) == 2


def test_source_model_validation() -> None:
    source = Source(
        id=uuid4(),
        agent_id=uuid4(),
        platform="gutenberg",
        external_id="3330",
        external_url="https://www.gutenberg.org/ebooks/3330",
        title="The Analects",
        author="Confucius",
        emos_group_id="group",
    )

    assert source.title == "The Analects"
