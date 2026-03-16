# Contract: Matrix Events (Appservice + Message Send)

**Scope**: Synapse → Bibliotalk Matrix adapter → Agent core → Synapse
**Room kinds**: Archive Rooms (public, read-only) and Dialogue Rooms (private, interactive)

This contract defines the minimal Matrix event shapes that the Matrix adapter accepts and relies on, plus the outbound message payload guarantees (including citations).

## Inbound: Appservice Transactions

Synapse delivers events via:

- `PUT /_matrix/app/v1/transactions/{txn_id}`
- `POST /_matrix/app/v1/transactions/{txn_id}`

### Authentication (MUST)

The Matrix adapter MUST authenticate Synapse using the configured appservice `hs_token`.

Rules:
- The token MUST be accepted via `access_token` query param (Synapse default).
- The token MAY also be accepted via `Authorization: Bearer <token>` for tooling compatibility.
- Requests with missing/invalid tokens MUST be rejected as unauthorized and MUST NOT be processed.

### Transaction Body

The request body MUST include:

```json
{
  "events": [<MatrixEvent>, ...]
}
```

Unknown top-level fields are ignored.

### Supported MatrixEvent Types (MVP)

The Matrix adapter explicitly models and handles:

1) `m.room.message` (text messages only)
2) `m.room.member` (membership changes for Spirit virtual users)

All other event types are ignored.

---

## Inbound: `m.room.message` (text)

Required fields:

- `type`: `"m.room.message"`
- `room_id`: Matrix room id (`!abc:server`)
- `sender`: Matrix user id (`@alice:server`)
- `content.msgtype`: `"m.text"` or `"m.notice"`
- `content.body`: message body (string)

Optional fields used for routing/loop prevention:

- `content.m.mentions.user_ids`: list of mentioned Matrix user ids
- `content.m.relates_to.rel_type`: if `"m.replace"`, the event is treated as an edit and ignored

**Rules (MUST)**:

1. Messages originating from Spirit virtual users (e.g., `sender` matches the `@bt_` namespace) MUST be ignored to prevent bot loops.
2. Messages in an Archive Room MUST be ignored (Archive Rooms are non-interactive).
3. Only text (`m.text` / `m.notice`) messages are eligible for routing.
4. Edit events (`m.replace`) MUST be ignored for MVP.

**Routing (Dialogue Rooms only)**:

1. If `m.mentions.user_ids` contains one or more Spirit virtual user IDs, the addressed Spirit(s) are those mentioned users.
2. Otherwise, if the message body contains one or more Spirit user IDs (literal `@bt_...` mentions), those Spirit(s) are addressed.
3. Otherwise, if the Dialogue Room contains exactly one Spirit member (best-effort membership index), that Spirit is addressed.
4. Otherwise, no Spirit responds.

---

## Inbound: `m.room.member`

Required fields:

- `type`: `"m.room.member"`
- `room_id`
- `state_key`: the membership target user id (Spirit virtual user is `@bt_...`)
- `content.membership`: `"invite" | "join" | "leave" | "ban"`

**Rules (MUST)**:

1. On `invite` for a known Spirit virtual user, the system MUST join the room as that user.
2. On `join`/`leave`/`ban`, the system updates its best-effort in-memory room→Spirit membership index for Dialogue Room routing.

---

## Outbound: Spirit Message Payload (Client-Server API)

Spirit text messages are sent via Matrix Client-Server API as the Spirit virtual user using the appservice `as_token` and the `user_id` masquerade parameter.

### Required Fields

The Matrix adapter MUST send content shaped like:

```json
{
  "msgtype": "m.text",
  "body": "…",
  "format": "org.matrix.custom.html",
  "formatted_body": "…",
  "com.bibliotalk.citations": {
    "version": "1",
    "items": [<Citation>, ...]
  }
}
```

**Rules (MUST)**:

1. `body` MUST contain visible citation markers corresponding to the structured citations (marker style is implementation-defined and adapter-owned, but MUST be stable and unambiguous within Matrix).
2. `com.bibliotalk.citations.items` MUST conform to `specs/001-matrix-mvp/contracts/citation-schema.md`.
3. For voice calls, the system MUST post a text transcript message into the Dialogue Room using the same payload shape (citations included when available).

### Optional: Streaming delivery (SHOULD for MVP UX)

To approximate “streaming responses” in Element, the Matrix adapter SHOULD stream the Spirit response by:
- sending an initial `m.room.message`, then
- issuing one or more `m.replace` edits to update `body` / `formatted_body` as text arrives, and finally
- finishing with a last edit that represents the final message (and includes the final structured citations).

Inbound edit events are still ignored for routing (see Rules above).
