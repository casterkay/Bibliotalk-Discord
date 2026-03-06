# Contract: Matrix Events (agents_service AppService)

**Owner (runtime)**: `services/agents_service/src/matrix/events.py` and `services/agents_service/src/matrix/appservice.py`  
**Scope**: Synapse → `agents_service` appservice transactions and Ghost message send payloads.

This contract defines the minimal Matrix event shapes that `agents_service` accepts and relies on, plus the outbound message payload guarantees (including citations).

## Inbound: Appservice Transactions

Synapse delivers events via:

- `PUT /_matrix/app/v1/transactions/{txn_id}`
- `POST /_matrix/app/v1/transactions/{txn_id}`

### Transaction Body

The request body MUST include:

```json
{
  "events": [<MatrixEvent>, ...]
}
```

Unknown top-level fields are ignored.

### Supported MatrixEvent Types

`agents_service` explicitly models and handles:

1) `m.room.message` (text messages only)
2) `m.room.member` (membership changes for Ghost virtual users)

All other event types are ignored.

### `m.room.message` (text)

Required fields:

- `type`: `"m.room.message"`
- `room_id`: Matrix room id (`!abc:server`)
- `sender`: Matrix user id (`@alice:server`)
- `content.msgtype`: `"m.text"` or `"m.notice"`
- `content.body`: message body (string)

Optional fields used for routing/loop prevention:

- `content.m.mentions.user_ids`: list of mentioned Matrix user ids
- `content.m.relates_to.rel_type`: if `"m.replace"`, the event is treated as an edit and ignored

Rules:

- Messages from Ghost virtual users (`sender` starts with `@bt_`) MUST be ignored to prevent bot loops.
- Messages in profile rooms (`profile_rooms` table) MUST be ignored (no AI response).

### `m.room.member`

Required fields:

- `type`: `"m.room.member"`
- `room_id`
- `state_key`: the membership target user id (Ghost virtual user is `@bt_...`)
- `content.membership`: `"invite" | "join" | "leave" | "ban"`

Rules:

- On `invite` for a known Ghost virtual user, `agents_service` MUST join the room as that user.
- On `join`/`leave`/`ban`, `agents_service` updates its best-effort in-memory room→Ghost index for DM routing.

## Outbound: Ghost Message Payload (Client-Server API)

Ghost text messages are sent via Matrix Client-Server API as the Ghost virtual user (`user_id` query param) using the appservice `as_token`.

### Required Fields

`agents_service` MUST send content shaped like:

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

- `body` MUST contain inline citation markers (`[^N]`) for each delivered citation (or `agents_service` MUST append missing markers).
- `com.bibliotalk.citations.items` MUST conform to `contracts/citation-schema.md`.

