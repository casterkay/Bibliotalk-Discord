# Contract: EverMemOS (EMOS) Client

**Owner**: `packages/bt_common/src/evermemos_client.py`  
**Direction**: Bibliotalk → EverMemOS API (via `evermemos` SDK wrapper)  
**Base URL**: configured per agent via `agent_emos_config.emos_base_url`

This contract describes the *logical* request/response shapes and ID conventions used by Bibliotalk. Actual EverMemOS deployments may vary in API versioning/path strings; contract tests should validate shapes rather than brittle URL literals.

## Headers

All requests include:
- `Content-Type: application/json`
- `Authorization: Bearer {emos_api_key}` (optional; depends on instance)

## Endpoints (per `BLUEPRINT.md`)

### POST `/api/v1/memories` — Memorize

Store a single segment as a memory message.

**Request**:
```json
{
  "message_id": "{agent_id}:{platform}:{external_id}:seg:{seq}",
  "create_time": "2025-01-15T10:00:00Z",
  "sender": "{agent_id}",
  "content": "segment text",
  "group_id": "{agent_id}:{platform}:{external_id}",
  "group_name": "source title",
  "role": "assistant"
}
```

**Response (200)**:
```json
{
  "status": "ok",
  "message": "...",
  "result": {
    "saved_memories": [],
    "count": 0,
    "status_info": "extracted"
  }
}
```

### GET `/api/v1/memories/search` — Retrieve

Search agent memories.

**Request** (body shape, transport may vary by SDK):
```json
{
  "query": "user's question",
  "user_id": "{agent_id}",
  "retrieve_method": "rrf",
  "memory_types": ["episodic_memory"],
  "top_k": 8
}
```

**Response (200)**:
```json
{
  "status": "ok",
  "result": {
    "memories": [
      {
        "episodic_memory": [
          {
            "summary": "...",
            "group_id": "{agent_id}:{platform}:{external_id}",
            "importance_score": 0.85
          }
        ]
      }
    ]
  }
}
```

### POST `/api/v1/memories/conversation-meta` — Save Metadata

Set source-level metadata for a `group_id` (one call per source).

**Request** (shape may vary by EMOS version; include `group_id` + human metadata):
```json
{
  "group_id": "{agent_id}:{platform}:{external_id}",
  "name": "Episode Title",
  "description": "https://...",
  "tags": ["podwise", "podcast"],
  "scene_desc": {
    "description": "Ingested source metadata",
    "extra": {
      "platform": "podwise",
      "source_url": "https://...",
      "title": "Episode Title"
    }
  }
}
```

## Error Envelope

EverMemOS errors are normalized into typed exceptions in the wrapper. If an instance returns a JSON error envelope, it is expected to look like:

```json
{
  "status": "failed",
  "code": "INVALID_PARAMETER",
  "message": "Human-readable error",
  "timestamp": "2025-01-15T10:30:00+00:00",
  "path": "/api/v1/memories"
}
```

Notes:
- `path` may vary across versions (e.g., `/api/v0/...`). Treat it as informational.

## Retry Policy

- Do not retry 4xx (validation/auth/client errors).
- Retry 5xx and connection/timeouts with exponential backoff (default: 3 attempts).
