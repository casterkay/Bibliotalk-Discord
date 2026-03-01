# Contract: EMOS Client

**Service**: bt-common → EverMemOS HTTP API
**Direction**: bt-common calls EMOS
**Base URL**: Configured per agent via `agent_emos_config.emos_base_url`

## Headers

All requests include:
- `Content-Type: application/json`
- `X-Organization-Id: {emos_org_id}` (if configured)
- `X-Space-Id: {emos_space_id}` (if configured)
- `X-API-Key: {emos_api_key}` (if configured)

## Endpoints

### POST /api/v1/memories — Memorize

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
    "status_info": "extracted" | "accumulated"
  }
}
```

### GET /api/v1/memories/search — Retrieve

Search agent memories. Uses JSON body on GET (per EMOS API design).

**Request** (JSON body):
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
    ],
    "total_count": 5,
    "has_more": false
  }
}
```

### POST /api/v1/memories/conversation-meta — Set Metadata

Set source-level metadata for a group.

**Request**:
```json
{
  "version": "1.0.0",
  "scene": "group_chat",
  "scene_desc": {
    "description": "Podcast episode transcript",
    "extra": {
      "platform": "taddy",
      "source_url": "https://...",
      "title": "Episode Title",
      "speakers": ["Speaker A", "Speaker B"]
    }
  },
  "name": "Episode Title",
  "group_id": "{agent_id}:{platform}:{external_id}",
  "created_at": "2025-01-15T10:00:00Z",
  "tags": ["taddy", "podcast"]
}
```

## Error Envelope

All error responses:
```json
{
  "status": "failed",
  "code": "INVALID_PARAMETER" | "RESOURCE_NOT_FOUND" | "SYSTEM_ERROR",
  "message": "Human-readable error",
  "timestamp": "2025-01-15T10:30:00+00:00",
  "path": "/api/v1/memories"
}
```

## Retry Policy

- 4xx errors: do not retry (client error)
- 5xx errors: retry with exponential backoff (max 3 attempts,
  base delay 1s, backoff factor 2x)
- Connection errors: retry with same policy
