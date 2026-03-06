# Contract: Discussion Floor Control

**Service**: per-room Discussion Controller inside `agents_service`  
**Scope**: multi-agent voice discussions (Matrix-native); optional coordination for multi-agent text streaming

## Core Principles

1. Exactly one active speaker per room at any time.
2. User speech/message has absolute preemption priority.
3. Ghost runners MAY post text to Matrix directly; only voice/audio output is floor-gated.
4. Every in-flight agent generation is cancellable.

## Identifiers

- `agent_id`: the Ghost’s UUID (`agents.id`)
- `matrix_user_id`: Matrix virtual user (`agents.matrix_user_id`)
- `room_id`: Matrix room id (e.g. `!abc:server`)

Do not overload Matrix user IDs as agent IDs.

## Floor States

```text
IDLE
USER_SPEAKING(matrix_user_id)
AGENT_SPEAKING(agent_id, generation_id)
```

State transitions:
- `IDLE -> USER_SPEAKING` on user VAD start
- `IDLE -> AGENT_SPEAKING` on grant of queued request
- `AGENT_SPEAKING -> USER_SPEAKING` on user barge-in (cancel required)
- `AGENT_SPEAKING -> IDLE` on completion/timeout/cancel
- `USER_SPEAKING -> IDLE` on end-of-utterance

## `REQUEST_FLOOR`

Ghost runners submit at most one outstanding request per room (voice/audio only).

```json
{
  "type": "REQUEST_FLOOR",
  "room_id": "!room:server",
  "agent_id": "00000000-0000-0000-0000-000000000000",
  "force": false,
  "reason": "Direct answer to user question",
  "urgency": 0.7,
  "relevance": 0.9,
  "estimate_ms": 12000,
  "max_tokens": 500
}
```

Rules:
- `force=true` may preempt only an active `AGENT_SPEAKING` holder.
- While `USER_SPEAKING`, agents may send `REQUEST_FLOOR` but must use `force=false`.
- The controller may clamp `estimate_ms` and `max_tokens`.
- The controller enforces cooldowns and force-rate limits.

## Scheduler Contract

When the floor is available, choose the highest score subject to hard constraints.

Hard constraints:
- Never preempt user speech.
- One active speaker max.
- Per-agent cooldown and max continuous speak window.

Score function:
`score = w_m * mention_boost + w_r * relevance + w_u * urgency + w_f * fairness + w_e * evidence`

Where:
- `mention_boost`: latest user utterance directly addresses that agent
- `relevance`: fit to current conversational context (includes topic coherence)
- `evidence`: grounded retrieval readiness for the likely response

## Cancellation Contract

Each granted turn has a `generation_id` and cancellation token.

The controller must support:
- `CANCEL(generation_id, reason)` on user barge-in, force-preemption, or explicit stop
- immediate stop for text streaming and voice TTS output
- best-effort acknowledgement via logs/metrics

## Streaming Contract

Text:
1. (Optional) Post placeholder message as speaking Ghost.
2. (Optional) Stream text via Matrix edits.
3. (Optional) Finalize message.
4. (Optional) Attach validated citations in the final event (`com.bibliotalk.citations`).

Voice:
1. Only the floor holder is unmuted for TTS emission.
2. User VAD start mutes Ghost audio and triggers cancellation.
3. Transcript and citations are posted to the room’s text thread.

## Determinism and Audit

- Controller records floor decisions and preemption events to `chat_history` and logs with `room_id`, `agent_id`, `generation_id`, and `reason`.
- Tie-break rules are deterministic (e.g., oldest request wins on equal score).
