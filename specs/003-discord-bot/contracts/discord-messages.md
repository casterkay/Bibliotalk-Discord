# Contract: Discord Message Shapes

**Used by:** `discord_service/src/bot/` · `discord_service/src/feed/` · tests
**Date:** 2026-03-07

All inbound and outbound Discord message interactions are represented by typed Pydantic models at the bot boundary before any business logic is applied.

---

## Inbound: DM Message

```python
from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel


class InboundDM(BaseModel):
    """A direct message received by a figure bot from a Discord user."""

    discord_message_id: str      # Discord snowflake string
    discord_user_id: str         # sender's Discord user ID
    discord_channel_id: str      # DM channel ID
    figure_id: uuid.UUID         # resolved from the receiving bot's identity
    content: str                 # raw message text (stripped of bot mention)
    received_at: datetime
```

---

## Outbound: DM Response

```python
class OutboundDMResponse(BaseModel):
    """
    A grounded response sent back to the user.

    - response_text contains only inline markdown links of the form
      [text](https://www.bibliotalk.space/memory/{id}).
    - No citation indices. No trailing Sources: block.
    - If evidence_used is empty, response_text MUST be the no-evidence message.
    """

    discord_channel_id: str
    response_text: str           # final validated Markdown text ≤ 2000 chars
    evidence_used: list[str]     # memory_url values that survived validation
    no_evidence: bool = False    # True when sent because validation left nothing
```

### Formatting rules

- `response_text` MUST be ≤ 2,000 characters (Discord per-message limit)
- Long responses MUST be split at sentence boundaries into multiple `OutboundDMResponse` objects with the same `discord_channel_id`
- Inline links format: `[visible text](https://www.bibliotalk.space/memory/{id})`
- `no_evidence` responses use a fixed template: *"I couldn't find relevant supporting evidence for that question."*

---

## Outbound: Feed Parent Message

```python
class FeedParentMessage(BaseModel):
    """
    The parent message posted to the figure's feed channel for a newly ingested video.
    Exactly one per source_id. Idempotency checked against discord_posts before sending.
    """

    figure_id: uuid.UUID
    source_id: uuid.UUID
    channel_id: str              # from DiscordMap.channel_id
    text: str                    # "{title}\n{source_url}" — max 2000 chars
```

---

## Outbound: Feed Thread Batch Message

```python
class FeedBatchMessage(BaseModel):
    """
    One transcript batch message posted inside a per-video thread.
    Maps 1:1 to a TranscriptBatch row. Idempotency checked by batch_id.
    """

    figure_id: uuid.UUID
    source_id: uuid.UUID
    batch_id: uuid.UUID
    thread_id: str               # Discord thread snowflake, set after thread creation
    text: str                    # verbatim transcript text — max 2000 chars
    seq_label: str               # e.g. "[00:01:23]" derived from start_ms
```

### Feed posting rules

1. Post `FeedParentMessage` → record `parent_message_id` in `discord_posts`.
2. Create thread attached to parent message → record `thread_id` in `discord_posts`.
3. Post `FeedBatchMessage` items in `start_seq` order, one at a time.
4. After each successful post, update `discord_posts.post_status = "posted"` and `transcript_batches.posted_to_discord = True`.
5. On retry: skip any `batch_id` with `post_status = "posted"` in `discord_posts`.
6. No two messages are posted within less than 1 second (sequential, rate-limit-safe).

---

## Error Handling

| Scenario                                         | Action                                                                          |
| ------------------------------------------------ | ------------------------------------------------------------------------------- |
| Discord 429 (rate limit)                         | Honour `retry_after`; re-enqueue the current batch message                      |
| Discord 403 (missing permissions)                | Log structured error; mark `post_status = "failed"`; do not retry automatically |
| Discord 500/503                                  | Exponential backoff up to 3 retries; then mark `post_status = "failed"`         |
| Thread creation succeeds, first batch post fails | Thread ID is recorded; retry starts from the first unposted batch               |
