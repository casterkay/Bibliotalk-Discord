# Contract: Archive Publication (v1)

**Purpose**: Define how ingested Sources/Segments are published into an Agent’s Archive Room in an idempotent, retry-safe way.

This contract is platform-specific to Matrix (because Archive Rooms are Matrix rooms), but service-agnostic: ingestion produces publish intents; the Matrix adapter performs posting.

---

## Archive Thread Shape

For each `Source` ingested for an `Agent`, the system publishes exactly one thread in that Agent’s Archive Room:

- **Root message**: source summary (title, canonical URL, optional metadata), sourced from ingestion / EverMemOS metadata (e.g., episodic memory) rather than newly generated AI text
- **Replies**: ordered verbatim transcript excerpt bodies (`Segment.seq` ascending)

The rendered body format is implementation-defined but MUST remain:
- deterministic
- stable enough for idempotency mapping
- purely verbatim for segment reply content (no AI summaries in replies)

---

## Publish Intent Object

The system persists publish intents as durable rows (exact storage is implementation-defined) with a stable idempotency key.

### Root intent

```json
{
  "platform": "matrix",
  "kind": "archive.thread_root",
  "agent_id": "uuid",
  "room_id": "!archive:server",
  "source_id": "uuid",
  "segment_id": null,
  "idempotency_key": "matrix:archive:{agent_id}:{source_id}:root"
}
```

### Reply intent

```json
{
  "platform": "matrix",
  "kind": "archive.thread_reply",
  "agent_id": "uuid",
  "room_id": "!archive:server",
  "source_id": "uuid",
  "segment_id": "uuid",
  "idempotency_key": "matrix:archive:{agent_id}:{source_id}:seg:{seq}"
}
```

Rules:
- The intent set is derivable deterministically from `(agent_id, source_id, segments ordered by seq)`.
- The system MUST enforce uniqueness on `idempotency_key`.

---

## Idempotency and Retry Guarantees

- Publishing the same intent multiple times MUST result in at most one platform event (no duplicates).
- If a thread root exists but replies are partially missing, re-running publication MUST post only missing replies.
- If publication fails due to transient platform errors, the system MUST record the error and retry later.
- Permanent errors MUST not hot-loop; they MUST be recorded with safe metadata and require operator intervention or a backoff strategy.
