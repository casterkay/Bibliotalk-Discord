import time

from bt_agent.guards import RateLimiter


def test_rate_limiter_enforces_5_second_cooldown_per_room() -> None:
    limiter = RateLimiter(cooldown_seconds=5)
    now = time.monotonic()

    assert limiter.allow("!room:example", now=now)
    assert not limiter.allow("!room:example", now=now + 4.9)


def test_rate_limiter_allows_messages_after_cooldown_expires() -> None:
    limiter = RateLimiter(cooldown_seconds=5)
    now = time.monotonic()

    assert limiter.allow("!room:example", now=now)
    assert limiter.allow("!room:example", now=now + 5.1)


def test_rate_limiter_tracks_rooms_independently() -> None:
    limiter = RateLimiter(cooldown_seconds=5)
    now = time.monotonic()

    assert limiter.allow("!roomA:example", now=now)
    assert limiter.allow("!roomB:example", now=now)
    assert not limiter.allow("!roomA:example", now=now + 1)
    assert not limiter.allow("!roomB:example", now=now + 1)
