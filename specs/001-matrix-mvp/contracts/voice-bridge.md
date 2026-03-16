# Contract: Voice Bridge Protocol (v1)

**Participants**:
- **Voice sidecar**: joins MatrixRTC/Element Call, handles WebRTC media, Opus encode/decode
- **Agent core**: manages voice sessions, grounding, transcript + citations, and Ghost audio output

**Transport**: bidirectional WebSocket (one WS connection per active voice session)

This contract defines the minimum message types required for the 1:1 voice MVP in Dialogue Rooms.

---

## Audio Format Contract

### Sidecar → Agent core (inbound audio)
- Format: PCM
- Sample rate: 16 kHz
- Bit depth: 16-bit signed little-endian
- Channels: mono

### Agent core → Sidecar (outbound Ghost audio)
- Format: PCM
- Sample rate: 24 kHz
- Bit depth: 16-bit signed little-endian
- Channels: mono

If either side requires resampling, it MUST be explicit and tested.

---

## Session Lifecycle

### 1) Create session (HTTP)

`POST /v1/voice/sessions`

```json
{
  "platform": "matrix",
  "room_id": "!room:server",
  "agent_id": "uuid",
  "initiator_platform_user_id": "@alice:server"
}
```

Response:

```json
{
  "session_id": "uuid-or-ulid",
  "ws_url": "wss://.../v1/voice/ws?session_id=..."
}
```

### 2) WebSocket connect

Sidecar connects using the returned `ws_url`.

---

## WebSocket Message Types

All messages are JSON objects with:

```json
{
  "type": "…",
  "ts": "2026-03-16T12:00:00Z",
  "payload": { }
}
```

### Sidecar → Agent core

#### `call.started`

```json
{
  "type": "call.started",
  "ts": "…",
  "payload": {
    "call_id": "opaque-platform-id",
    "participants": ["@alice:server", "@bt_ghost_confucius:server"]
  }
}
```

#### `audio.chunk`

Carries raw PCM bytes (base64 encoded).

```json
{
  "type": "audio.chunk",
  "ts": "…",
  "payload": {
    "pcm16k_b64": "…"
  }
}
```

#### `audio.stream_end`

Signals that the inbound stream paused/ended and any cached audio should be flushed. This is aligned with Gemini Live’s `audio_stream_end`.

```json
{
  "type": "audio.stream_end",
  "ts": "…",
  "payload": { }
}
```

#### `vad.start` / `vad.end` (optional)

If the agent core is configured to disable automatic VAD and use manual turn-taking, the sidecar MAY emit `vad.start` / `vad.end`. For MVP, automatic VAD is preferred; these events are typically not needed (grounded on `docs/knowledge/gemini-live-api.md`).

#### `call.ended`

```json
{
  "type": "call.ended",
  "ts": "…",
  "payload": {
    "reason": "user_hangup|network_error|timeout"
  }
}
```

### Agent core → Sidecar

#### `transcription.input` / `transcription.output`

For MVP, voice transcripts are provided by Gemini Live when configured with `input_audio_transcription` and `output_audio_transcription` (grounded on `docs/knowledge/gemini-live-api.md`). The agent core forwards these to the sidecar.

```json
{
  "type": "transcription.input",
  "ts": "…",
  "payload": { "text": "…", "is_final": true }
}
```

```json
{
  "type": "transcription.output",
  "ts": "…",
  "payload": { "text": "…", "is_final": false }
}
```

#### `audio.chunk`

Ghost audio output, raw PCM bytes (base64 encoded).

```json
{
  "type": "audio.chunk",
  "ts": "…",
  "payload": {
    "pcm24k_b64": "…"
  }
}
```

#### `turn.end`

Signals the end of the Ghost’s response turn.

```json
{
  "type": "turn.end",
  "ts": "…",
  "payload": {
    "has_citations": true
  }
}
```

#### `error`

```json
{
  "type": "error",
  "ts": "…",
  "payload": {
    "code": "VOICE_BACKEND_UNAVAILABLE",
    "message": "Safe human-readable message"
  }
}
```

#### `interrupted`

Emitted when the in-progress Ghost output should be stopped immediately (e.g., barge-in / VAD interruption, user cancel, or a newer turn supersedes the current one).

```json
{
  "type": "interrupted",
  "ts": "…",
  "payload": { "reason": "vad|cancelled|superseded" }
}
```

---

## Reliability Requirements

- The sidecar MUST tolerate transient WS disconnects by reconnecting and either resuming the session or cleanly restarting it (implementation-defined strategy, but must not create orphan sessions).
- The agent core MUST support barge-in / interruption. With automatic VAD, interruption SHOULD be detected via the Gemini Live session and surfaced to the sidecar so it can stop playback immediately.
- On any fatal error, the agent core MUST emit an `error` message and then allow the WS to close cleanly.
