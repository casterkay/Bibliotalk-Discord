# Contract: Citation Schema

**Owner**: `services/agents_service/src/models/citation.py`  
**Used by**: `agents_service` (Matrix events + chat_history persistence)

This contract defines the structured citation payload used to keep Ghost responses verifiable (**言必有據**).

## Citation Object

```json
{
  "index": 1,
  "segment_id": "uuid",
  "emos_message_id": "{agent_id}:{platform}:{external_id}:seg:{seq}",
  "source_title": "The Analects, Book II",
  "source_url": "https://www.gutenberg.org/ebooks/3330",
  "quote": "Learning without reflection is a waste...",
  "platform": "gutenberg",
  "timestamp": "2025-01-15T10:00:00Z"
}
```

Notes:
- `timestamp` is optional and may be either an ISO date or ISO date-time.
- `quote` MUST be a substring of the canonical `segments.text` for the referenced `segment_id`.

## Matrix Event Extension

Ghost responses include structured citations in the event content under `com.bibliotalk.citations`:

```json
{
  "msgtype": "m.text",
  "body": "Response with citation markers...",
  "format": "org.matrix.custom.html",
  "formatted_body": "Response with <sup>[1]</sup>...",
  "com.bibliotalk.citations": {
    "version": "1",
    "items": [<Citation>, ...]
  }
}
```

## Validation Rules

Before posting any Ghost response:
1. Verify every cited `segment_id` exists in `segments` and belongs to the responding agent.
2. Verify `quote` is a substring of the canonical `segments.text`.
3. Strip citations that fail validation; log a warning.
4. Cross-agent citations are always invalid (`segments.agent_id` must match the responding agent’s UUID).

## Evidence Object (internal)

`memory_search` returns evidence items used to construct citations:

```json
{
  "segment_id": "uuid",
  "emos_message_id": "...",
  "source_title": "...",
  "source_url": "...",
  "text": "full segment text",
  "platform": "podwise"
}
```
