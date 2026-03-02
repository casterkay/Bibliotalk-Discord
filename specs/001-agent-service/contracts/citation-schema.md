# Contract: Citation Schema

**Service**: bt_common (shared across agents_service, ingestion_service)
**Format**: Pydantic models, embedded in Matrix events and chat_history

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
  "timestamp": "2025-01-15"
}
```

## Matrix Event Extension

Clone responses include structured citations in the event content:

```json
{
  "msgtype": "m.text",
  "body": "Response with [^1] markers...\n\n──────────\nSources:\n[1] Title (platform:id)",
  "format": "org.matrix.custom.html",
  "formatted_body": "Response with <sup>[1]</sup>...<hr><b>Sources:</b>...",
  "com.bibliotalk.citations": {
    "version": "1",
    "items": [<Citation>, ...]
  }
}
```

## Validation Rules

Before posting any Clone response:
1. Parse citation markers from response text
2. Verify each `segment_id` exists in segments table for this agent
3. Verify each `quote` is a substring of `segments.text`
4. Strip citations that fail validation; log warning
5. Cross-agent citations are always invalid (segment.agent_id
   must match the responding agent's ID)

## Evidence Object (internal, returned by memory_search tool)

```json
{
  "segment_id": "uuid",
  "emos_message_id": "...",
  "source_title": "...",
  "source_url": "...",
  "text": "full segment text",
  "platform": "podwise" | "gutenberg" | "youtube"
}
```
