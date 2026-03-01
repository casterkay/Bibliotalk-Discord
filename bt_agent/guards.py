"""Message guardrails."""

from __future__ import annotations

import time


class RateLimiter:
    def __init__(self, cooldown_seconds: float = 5.0):
        self.cooldown_seconds = cooldown_seconds
        self._last_seen: dict[str, float] = {}

    def allow(self, room_id: str, *, now: float | None = None) -> bool:
        current = now if now is not None else time.monotonic()
        previous = self._last_seen.get(room_id)
        if previous is not None and (current - previous) < self.cooldown_seconds:
            return False
        self._last_seen[room_id] = current
        return True
