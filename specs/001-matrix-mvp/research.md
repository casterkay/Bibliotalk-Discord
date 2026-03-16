# Research: Matrix MVP (Archive + Dialogue + Voice)

**Phase 0 output for:** `001-matrix-mvp`
**Date:** 2026-03-16
**Resolves all NEEDS CLARIFICATION items from Technical Context in** `/Users/tcai/Projects/Bibliotalk/specs/001-matrix-mvp/plan.md` *(none outstanding)*

---

## 1. Platform-Agnostic Core: Normalize “Turn In / Turn Out”

**Decision:** Define a platform-independent “conversation turn” input and a platform-independent “agent result” output. All platform adapters (Matrix now, Discord later) translate native events into the turn contract, invoke the agent core, and render the result into native platform message formats.

**Rationale:** Bibliotalk’s trust invariants (grounding-first, cross-Spirit isolation, citation validation) must not be re-implemented per platform. A single core makes correctness testable once and reusable.

**Alternatives considered:**
- Duplicate logic per platform adapter: rejected due to inevitable behavior drift and citation regressions.
- Put all platform code inside the agent runtime: rejected because it couples deployment and makes adapters hard to test and replace.

---

## 2. Matrix Room Taxonomy: Archive Rooms vs Dialogue Rooms

**Decision:** Adopt two immutable Matrix room kinds:

- **Archive Room**: public, read-only; ingestion-backed; never interactive. Per source, the thread root is a deterministic source summary (from ingestion / EverMemOS metadata) and replies are ordered verbatim transcript excerpts.
- **Dialogue Room**: private (invite-only) conversational room; Spirits can respond; may host voice calls.

**Rationale:** The “no AI in public” rule is best enforced structurally, not via mutable flags. A hard taxonomy prevents accidental leakage of Spirit-generated content into public contexts and makes policy simple to test.

**Alternatives considered:**
- Per-room “AI enabled” toggle state event: rejected because it is mutable and error-prone.
- Allow AI in Archive Rooms but “discourage” it: rejected as incompatible with “zero AI responses” requirement.

---

## 3. Matrix Appservice Event Handling

**Decision:** Handle only the minimal Matrix event set required for the MVP:

- Inbound appservice transactions containing `m.room.message` (text) and `m.room.member` (membership changes for Spirit virtual users).
- Ignore edits (`m.replace`), non-text messages, and all events originating from Spirit virtual users (loop prevention).

**Rationale:** MVP correctness depends on a small set of deterministic routing rules and guardrails (Archive vs Dialogue, mention-based addressing, no bot loops). Handling fewer event types reduces failure surface and prevents accidental interactive behavior in Archive Rooms.

**Alternatives considered:**
- Handle all timeline events and infer meaning later: rejected as unnecessary complexity for MVP.
- Respond to unaddressed messages in multi-Spirit Dialogue Rooms: rejected because it creates noisy, nondeterministic group behavior.

---

## 3.1 Matrix Adapter Runtime: Node/TypeScript (matrix-js-sdk)

**Decision:** Implement `matrix_service` in Node.js/TypeScript using `matrix-js-sdk` (and a minimal HTTP server framework) rather than relying on a Python Matrix SDK.

**Rationale:** The Matrix ecosystem’s most actively used SDK is `matrix-js-sdk` (Element’s primary stack). Using it reduces integration risk for AppService + Client-Server interactions and improves long-term maintainability.

**Alternatives considered:**
- Python Matrix SDK: rejected for MVP due to higher maintenance risk and SDK surface mismatches with Element/MatrixRTC realities.
- Merging voice sidecar into `matrix_service`: rejected because it increases blast radius; voice failures must not take down text chat (FR-023).

---

## 4. Citation Rendering and Machine-Readable Citation Payloads

**Decision:** Require every cited response to include:

- **Human-visible citation markers** in the message body (marker style is adapter-owned and implementation-defined per platform).
- **Machine-readable citation payloads** attached to the message (structured citation list) so clients and tools can render citations consistently.

**Rationale:** Marker-only citations are fragile; payload-only citations are invisible. Using both supports trust, debugging, and future UX improvements while preserving determinism in validation.

**Alternatives considered:**
- Only a trailing “Sources:” block: rejected because it is harder to associate claims with sources and is easier to spoof.
- Only structured payloads: rejected because users need visible citations inline.

---

## 5. Archive Publication: Idempotent Source Threads

**Decision:** Publish ingested content to Archive Rooms as per-source threads:

- Thread root = source summary (title + canonical URL + optional metadata).
- Thread replies = ordered verbatim segments (or batches when appropriate), each mapped to a stable idempotency key derived from `(agent, source, seq)`.

Re-running publication MUST not create duplicate roots or replies; partial failures must resume safely.

**Rationale:** Archive Rooms must remain a stable, auditable representation of “what the Spirit knows.” Idempotency is non-negotiable in the face of retries and restarts.

**Alternatives considered:**
- “Best effort” posting without persistence: rejected (duplicates and gaps accumulate over time).
- One message per source with all text: rejected (too large and loses ordering/location fidelity).

---

## 6. Voice MVP: Gemini Live-Powered Speech With Grounded Text Authority

**Decision:** In 1:1 voice calls, Gemini Live powers real-time speech I/O, but the **grounded text agent remains the authority** for content + citations:

1. User speech → transcription (speech recognition).
2. Transcript → grounded text agent turn (retrieval + citation validation).
3. Agent response text → speech synthesis.
4. Post a text transcript + citations to the Dialogue Room for every Spirit voice turn.

**Rationale:** This architecture preserves Bibliotalk’s core trust constraint (verifiable citations) while enabling a compelling voice experience. It isolates speech I/O concerns from grounding logic and makes the voice stack testable using recorded transcripts.

**Alternatives considered:**
- Let the live voice model directly call tools and produce citations: rejected for MVP due to increased complexity in mid-stream tool calls, cancellation, and deterministic validation.
- Voice-only without a posted transcript: rejected (citations must remain inspectable).

---

## 7. Voice Bridge Protocol: Sidecar ↔ Agent Core

**Decision:** Use a minimal, explicit bridge protocol between the voice sidecar and the agent core:

- Inbound: audio frames + stream boundaries (and optional manual VAD signals) + call/session lifecycle events.
- Outbound: Spirit audio frames + transcription events (from Gemini Live) + “end of turn” events + interruption + error notifications.

**Rationale:** Voice is inherently stateful and failure-prone. A typed bridge protocol prevents “stringly-typed” integration bugs and supports deterministic recovery and audit logging.

**Alternatives considered:**
- Sidecar calls ad-hoc HTTP endpoints: rejected because voice needs bidirectional streaming.
- Use the Matrix homeserver as a relay for audio/control: rejected (wrong abstraction; adds latency and complexity).

---

## 8. Observability and Audit

**Decision:** Require correlation IDs and structured logs across:

- Matrix appservice transactions (`txn_id`, `room_id`, `event_id`).
- Agent turns (`agent_id`, `turn_id`, evidence counts, citation validation outcomes).
- Archive publication (`source_id`, `segment_seq`, idempotency keys).
- Voice sessions (`session_id`, `room_id`, start/end, error reasons).

**Rationale:** Without first-class observability, debugging grounding or voice failures becomes ad-hoc and unreliable.

**Alternatives considered:**
- Minimal logging until production: rejected; observability must be designed in.
