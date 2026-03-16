# Contract: Agent Interaction API (v1)

**Purpose**: Provide a stable, platform-agnostic interface for Spirit interactions (text + voice) with first-class streaming.
**Primary caller (MVP)**: Matrix adapter
**Primary callee (MVP)**: agent core (`agents_service`)

This contract is intentionally minimal and designed to remain stable as additional platforms (e.g., Discord) are added.

**Design stance (MVP)**:
- Streaming is **first-class**. Callers SHOULD use Live Sessions for full-duplex interactions (users can send new inputs while the Spirit is streaming output).
- A non-streaming “turn” endpoint remains available as a compatibility fallback.

---

## Live Sessions (first-class)

Live Sessions provide full-duplex streaming over WebSocket. The agent core MAY implement the underlying streaming using Gemini Live (recommended for voice) or other providers, but it MUST uphold Bibliotalk’s grounding + citation validation invariants.

### Endpoint: Create a Live Session (HTTP)

`POST /v1/agents/{agent_id}/live/sessions`

#### Request Body

```json
{
  "platform": "matrix",
  "room_id": "!room:server",
  "initiator_platform_user_id": "@alice:server",
  "modality": "text"
}
```

Rules:
- `modality` is `text` or `voice`.
- For `modality=voice`, callers SHOULD expect audio streaming and transcription events.

#### Success Response

```json
{
  "session_id": "uuid-or-ulid",
  "ws_url": "wss://.../v1/agents/live/ws?session_id=..."
}
```

### Endpoint: Live Session WebSocket

`WS /v1/agents/live/ws?session_id=...`

#### Message Envelope

All messages MUST be JSON objects with:

```json
{
  "type": "…",
  "ts": "2026-03-16T12:00:00Z",
  "turn_id": "uuid-or-ulid",
  "payload": { }
}
```

Rules:
- `turn_id` scopes a single user input → Spirit output unit of work.
- Callers MAY send a new turn while a previous turn is still streaming. For MVP, the agent core MUST either:
  - support multiplexed streaming by `turn_id`, OR
  - cancel the in-progress turn and begin the newest turn (recommended; matches Gemini Live VAD interruption semantics).

#### Client → Agent core message types

##### `input.text`

```json
{
  "type": "input.text",
  "ts": "…",
  "turn_id": "…",
  "payload": { "text": "What did you say about learning?" }
}
```

##### `input.audio.chunk`

Carries raw PCM bytes (base64 encoded). Audio requirements are grounded on `docs/knowledge/gemini-live-api.md`.

```json
{
  "type": "input.audio.chunk",
  "ts": "…",
  "turn_id": "…",
  "payload": { "pcm16k_b64": "…" }
}
```

##### `input.audio.stream_end`

Signals a pause/end-of-stream boundary (flush any cached audio). This mirrors Gemini Live’s `audio_stream_end`.

```json
{
  "type": "input.audio.stream_end",
  "ts": "…",
  "turn_id": "…",
  "payload": { }
}
```

##### `input.cancel`

```json
{
  "type": "input.cancel",
  "ts": "…",
  "turn_id": "…",
  "payload": { "reason": "user_cancel|superseded" }
}
```

##### `input.context.append`

Adds context deterministically (ordered) to the session. This is the contract-level equivalent of Gemini Live’s `send_client_content`.

```json
{
  "type": "input.context.append",
  "ts": "…",
  "turn_id": "…",
  "payload": {
    "turns": [
      { "role": "user", "parts": [{ "text": "Earlier question…" }] },
      { "role": "model", "parts": [{ "text": "Earlier answer…" }] }
    ],
    "turn_complete": false
  }
}
```

Rules:
- `turn_id` MAY be a sentinel value for purely contextual updates (implementation-defined).
- This message is for context; it MUST NOT itself trigger a new Spirit response unless explicitly coupled with an `input.text` or `input.audio.*` turn.

#### Agent core → Client message types

##### `output.text.delta` / `output.text.final`

```json
{
  "type": "output.text.delta",
  "ts": "…",
  "turn_id": "…",
  "payload": { "text": "…partial…" }
}
```

```json
{
  "type": "output.text.final",
  "ts": "…",
  "turn_id": "…",
  "payload": { "text": "…final…" }
}
```

Rules:
- Citation markers are adapter-owned. The agent core emits plain text plus structured citations; adapters format per platform.

##### `output.citations.final`

```json
{
  "type": "output.citations.final",
  "ts": "…",
  "turn_id": "…",
  "payload": {
    "version": "1",
    "items": [<Citation>, ...]
  }
}
```

Rules:
- `items` MUST conform to `specs/001-matrix-mvp/contracts/citation-schema.md`.
- The agent core MUST validate citations before emitting this message.

##### `output.audio.chunk`

Spirit audio output, raw PCM bytes (base64 encoded).

```json
{
  "type": "output.audio.chunk",
  "ts": "…",
  "turn_id": "…",
  "payload": { "pcm24k_b64": "…" }
}
```

##### `output.transcription.input` / `output.transcription.output`

For voice sessions, transcriptions SHOULD be produced by Gemini Live (via `input_audio_transcription` / `output_audio_transcription`) and forwarded.

```json
{
  "type": "output.transcription.input",
  "ts": "…",
  "turn_id": "…",
  "payload": { "text": "…", "is_final": true }
}
```

```json
{
  "type": "output.transcription.output",
  "ts": "…",
  "turn_id": "…",
  "payload": { "text": "…", "is_final": false }
}
```

##### `output.interrupted`

Emitted when a turn is interrupted (e.g., voice activity / new input supersedes current generation). This is conceptually aligned with Gemini Live interruption semantics.

```json
{
  "type": "output.interrupted",
  "ts": "…",
  "turn_id": "…",
  "payload": { "reason": "vad|cancelled|superseded" }
}
```

##### `output.turn.end`

```json
{
  "type": "output.turn.end",
  "ts": "…",
  "turn_id": "…",
  "payload": { "no_evidence": false, "has_citations": true }
}
```

##### `error`

```json
{
  "type": "error",
  "ts": "…",
  "turn_id": "…",
  "payload": {
    "code": "INTERNAL_ERROR",
    "message": "Safe human-readable message"
  }
}
```

---

## Endpoint: Create a Turn (non-streaming fallback)

`POST /v1/agents/{agent_id}/turn`

### Request Body

```json
{
  "platform": "matrix",
  "room_id": "!room:server",
  "event_id": "$event:server",
  "sender_platform_user_id": "@alice:server",
  "sender_display_name": "Alice",
  "text": "What did you say about learning?",
  "mentions": ["@bt_spirit_confucius:server"],
  "timestamp": "2026-03-16T12:00:00Z",
  "modality": "text"
}
```

Rules:
- `mentions` MAY be empty.
- `event_id` MAY be null for voice turns (where there is no native message event).
- `modality` is `text` for normal messages and `voice` for voice transcript turns.

### Success Response

```json
{
  "text": "…",
  "citations": [
    {
      "segment_id": "uuid",
      "emos_message_id": "…",
      "source_title": "…",
      "source_url": "…",
      "quote": "…",
      "content_platform": "youtube",
      "timestamp": "2026-03-16T12:00:00Z"
    }
  ],
  "no_evidence": false
}
```

Rules:
- `citations` MAY be empty only when the response is an explicit “no evidence” response or the response is non-factual.
- If `no_evidence=true`, the `text` MUST explicitly communicate the lack of supporting evidence.

### Error Responses

Errors MUST be returned with a stable error shape:

```json
{
  "error": {
    "code": "AGENT_NOT_FOUND",
    "message": "Human-readable message safe for logs"
  }
}
```

Error codes (MVP minimum):
- `AGENT_NOT_FOUND`
- `AGENT_INACTIVE`
- `RATE_LIMITED`
- `UPSTREAM_MEMORY_UNAVAILABLE`
- `INTERNAL_ERROR`

---

## Non-Functional Contract Guarantees

- The agent core MUST enforce cross-Spirit isolation: responses for `{agent_id}` MUST never cite evidence owned by another agent.
- The agent core MUST validate citations before returning them in this API.
- The agent core MUST be cancellable per turn (implementation-specific cancellation mechanism; required for voice barge-in support).
