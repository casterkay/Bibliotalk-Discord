from __future__ import annotations

from datetime import UTC, datetime

import pytest
from ingestion_service.adapters.rss_feed import FeedEntry
from ingestion_service.domain.errors import AdapterError
from ingestion_service.pipeline.discovery import (
    DiscoveredVideo,
    compute_discovery_delta,
    discover_subscription,
)


def test_compute_discovery_delta_uses_last_seen_video_id() -> None:
    entries = [
        DiscoveredVideo(
            "vid-c",
            "C",
            "https://www.youtube.com/watch?v=vid-c",
            datetime(2024, 1, 3, tzinfo=UTC),
            None,
            {},
        ),
        DiscoveredVideo(
            "vid-b",
            "B",
            "https://www.youtube.com/watch?v=vid-b",
            datetime(2024, 1, 2, tzinfo=UTC),
            None,
            {},
        ),
        DiscoveredVideo(
            "vid-a",
            "A",
            "https://www.youtube.com/watch?v=vid-a",
            datetime(2024, 1, 1, tzinfo=UTC),
            None,
            {},
        ),
    ]

    delta = compute_discovery_delta(entries, last_seen_video_id="vid-a", last_published_at=None)

    assert [item.video_id for item in delta] == ["vid-b", "vid-c"]


def test_compute_discovery_delta_falls_back_to_published_at() -> None:
    entries = [
        DiscoveredVideo(
            "vid-c",
            "C",
            "https://www.youtube.com/watch?v=vid-c",
            datetime(2024, 1, 3, tzinfo=UTC),
            None,
            {},
        ),
        DiscoveredVideo(
            "vid-b",
            "B",
            "https://www.youtube.com/watch?v=vid-b",
            datetime(2024, 1, 2, tzinfo=UTC),
            None,
            {},
        ),
        DiscoveredVideo(
            "vid-a",
            "A",
            "https://www.youtube.com/watch?v=vid-a",
            datetime(2024, 1, 1, tzinfo=UTC),
            None,
            {},
        ),
    ]

    delta = compute_discovery_delta(
        entries,
        last_seen_video_id=None,
        last_published_at=datetime(2024, 1, 1, tzinfo=UTC),
    )

    assert [item.video_id for item in delta] == ["vid-b", "vid-c"]


@pytest.mark.anyio
async def test_discover_subscription_falls_back_to_rss() -> None:
    async def failing_yt_dlp(_: str):
        raise AdapterError("yt-dlp failed")

    async def fake_rss(_: str):
        return [
            FeedEntry(
                video_id="vid-a",
                url="https://www.youtube.com/watch?v=vid-a",
                title="Video A",
                published_at=datetime(2024, 1, 1, tzinfo=UTC),
                raw_meta={"feed_url": "https://example.com/feed"},
            )
        ]

    delta = await discover_subscription(
        "https://example.com/feed",
        yt_dlp_loader=failing_yt_dlp,
        rss_loader=fake_rss,
    )

    assert len(delta) == 1
    assert delta[0].video_id == "vid-a"
