# Feature Specification: Matrix MVP (Archive Rooms + Dialogue Rooms + Voice)

**Feature Branch**: `001-matrix-mvp`
**Created**: 2026-03-16
**Status**: Draft
**Input**: User description: "Looks great. One more spec: - Rename profile room to Archive Room and private room to Dialogue Room. Now write down the spec with high fidelity and precision in `specs/` (No. 001)"

## User Scenarios & Testing *(mandatory)*

### User Story 1 — Grounded Spirit Text Chat In a Dialogue Room (Priority: P1)

A user uses Element to chat with a Spirit in a **Dialogue Room** (a private DM or private group room). The Spirit responds in-character and only makes claims supported by the Spirit’s own ingested memory. Each non-trivial claim includes verifiable citations back to the original source material. If the Spirit cannot find relevant evidence, it explicitly says so rather than guessing.

The Spirit’s response MAY be streamed to the room as it is generated (Matrix adapters can approximate streaming via message edits). Users MUST be able to send a new message while the Spirit is streaming; the system MUST either multiplex or cancel/supersede the in-progress response.

**Why this priority**: This is the core user value of Bibliotalk: trustworthy, evidence-grounded conversation.

**Independent Test**: Create a Dialogue Room with a single Spirit, ask a question that should match known ingested material, and verify the Spirit responds with verifiable citations. Then ask an out-of-domain question and verify the Spirit declines due to lack of evidence.

**Acceptance Scenarios**:

1. **Given** a Dialogue Room that includes a user and a Spirit, **When** the user asks a question with supporting evidence in the Spirit’s memory, **Then** the Spirit replies in the same room with a cited answer and all citations are verifiable against the Spirit’s ingested source segments.
2. **Given** a Dialogue Room that includes a user and a Spirit, **When** the user asks a question with no relevant supporting evidence in the Spirit’s memory, **Then** the Spirit explicitly states it cannot find relevant supporting evidence and does not fabricate claims.
3. **Given** a Dialogue Room that includes multiple Spirits, **When** the user explicitly addresses (mentions) one Spirit, **Then** only the addressed Spirit responds.
4. **Given** a Dialogue Room that includes multiple Spirits, **When** the user does not explicitly address any Spirit, **Then** no Spirit responds (to avoid ambiguous or noisy multi-Spirit behavior).
5. **Given** a Dialogue Room, **When** a message is sent by a Spirit identity, **Then** the system ignores it for response generation to prevent bot loops.
6. **Given** a Spirit response containing citations, **When** the system validates the citations, **Then** any citation that fails verification is removed from the delivered response and the remaining response stays readable.
7. **Given** a Spirit is streaming a response in a Dialogue Room, **When** the user sends a new message, **Then** the system cancels or supersedes the in-progress response and responds to the newest message (with the same grounding + citation guarantees).

---

### User Story 2 — Browse a Spirit’s Archive Room in the Bibliotalk Space (Priority: P2)

A user browses the Bibliotalk Space and opens a Spirit’s **Archive Room** (public, read-only). The Archive Room is ingestion-backed and non-interactive: for each ingested source, it contains a thread whose root is a deterministic source summary (from ingestion / EverMemOS metadata) and whose replies are ordered verbatim transcript excerpts/segments.

**Why this priority**: Archive Rooms are the trust foundation of the product: users can directly inspect what the Spirit “knows” and where it came from.

**Independent Test**: Open an Archive Room for a Spirit and verify that the timeline contains only ingested content, can be read by any user, and cannot be used to interact with the Spirit (no AI replies).

**Acceptance Scenarios**:

1. **Given** a Spirit is available in the Bibliotalk Space, **When** a user opens the Spirit’s Archive Room, **Then** the user can read the room history without special permissions.
2. **Given** a source has been ingested for a Spirit, **When** the Archive Room is updated, **Then** the room contains a thread with a root source message and replies containing ordered verbatim segments with enough context to locate the passage (timestamps or section markers when available).
3. **Given** a user attempts to send a message in an Archive Room, **When** the message is submitted, **Then** the user is prevented from posting (read-only enforcement) and the system produces zero AI responses in that room.
4. **Given** the ingestion publisher is re-run for the same source, **When** the Archive Room is updated, **Then** duplicate threads or duplicate segment posts are not created for already-published content.

---

### User Story 3 — 1:1 Voice Call With a Spirit in a Dialogue Room (Priority: P3)

A user starts an Element voice call in a Dialogue Room and invites a Spirit. The Spirit participates in the call as a voice-enabled agent, responding with speech grounded in its memory. For every voice turn, the system also posts a parallel text transcript with citations in the same room (optionally as a thread) so the user can verify sources. Voice transcripts are sourced from the Gemini Live API’s built-in input/output transcription streams.

**Why this priority**: Voice calls are the most compelling demonstration of “Spirits feel real” while maintaining Bibliotalk’s core trust constraint (citations).

**Independent Test**: Start an Element call in a Dialogue Room with a Spirit, ask a question in speech, confirm the Spirit responds in speech, and confirm a text transcript with verifiable citations appears in the room for the same turn.

**Acceptance Scenarios**:

1. **Given** a Dialogue Room with a user and a Spirit, **When** the user starts a voice call and begins speaking, **Then** the Spirit responds in speech after the user finishes their utterance and a text transcript of the Spirit’s spoken answer is posted to the room with verifiable citations.
2. **Given** a voice call turn produces citations, **When** citations are validated, **Then** any invalid citations are removed before the transcript is posted.
3. **Given** a voice call drops unexpectedly, **When** the disconnection occurs, **Then** the system preserves any transcript captured so far and does not leave a “stuck” or orphaned voice session.
4. **Given** voice capability is temporarily unavailable, **When** a user tries to start or use voice in a Dialogue Room, **Then** the user receives a clear text notification and text chat remains available.
5. **Given** a user attempts to start a voice call in an Archive Room, **When** the request is made, **Then** the system rejects it (Archive Rooms are non-interactive).

---

### Edge Cases

- What happens when a Spirit is invited to a Dialogue Room but is not configured or is inactive?
- What happens when a user edits a message after sending it in a Dialogue Room?
- What happens when a Dialogue Room has multiple Spirits and a user addresses multiple Spirits in one message?
- What happens when a Spirit produces a response but the cited quote does not exactly match the underlying segment text?
- What happens when a source is ingested but Archive Room publication fails midway?
- What happens when two users talk to the same Spirit concurrently in separate Dialogue Rooms?
- What happens when voice session audio is received but speech recognition fails for a turn?
- What happens when a user speaks continuously for a long time or interrupts the Spirit mid-response?

## Requirements *(mandatory)*

### Functional Requirements

#### Platform-Agnostic Backend

- **FR-001**: The system MUST be architected to support multiple messaging platforms (Matrix first; Discord later) without duplicating core Spirit reasoning, grounding, and citation validation behavior. During the Matrix MVP refactor, Discord support MAY temporarily break.
- **FR-002**: The system MUST define a normalized representation of a conversation turn (sender, room, message content, addressed participant(s), and timing) so that platform adapters can route messages consistently.
- **FR-003**: The system MUST define a platform-independent response output format (response text + structured citations + optional evidence metadata) that adapters can render for each platform.

#### Room Taxonomy (Matrix)

- **FR-004**: The system MUST define exactly two immutable Matrix room kinds: **Archive Rooms** (public, read-only, non-interactive) and **Dialogue Rooms** (private, interactive).
- **FR-005**: The system MUST enforce that Spirits generate zero AI responses in Archive Rooms under all conditions.
- **FR-006**: Archive Rooms MUST be ingestion-backed: per source thread root is a deterministic source summary (from ingestion / EverMemOS metadata) and thread replies are ordered verbatim transcript excerpts/segments.
- **FR-007**: Dialogue Rooms MUST allow interactive Spirit participation in text; they MAY also host voice calls.
- **FR-007a**: The Matrix adapter MUST authenticate Synapse appservice requests using the configured `hs_token` before processing any transactions.

#### Grounded Text Chat (Dialogue Rooms)

- **FR-008**: For every eligible user message in a Dialogue Room, the addressed Spirit MUST search its memory before answering and MUST not answer from ungrounded speculation.
- **FR-009**: If no relevant evidence exists, the Spirit MUST explicitly say it cannot find relevant supporting evidence.
- **FR-010**: The system MUST ensure strict isolation: a Spirit MUST cite only from its own memory and ingested segments; cross-Spirit citations are invalid.
- **FR-011**: In Dialogue Rooms with multiple Spirits, the system MUST respond only for Spirits that are explicitly addressed by the user; ambiguous unaddressed messages produce no Spirit response.
- **FR-012**: The system MUST prevent response loops by ignoring messages sent by Spirit identities as triggers for further Spirit responses.

#### Citations (All Interactive Responses)

- **FR-013**: Every Spirit response that contains non-trivial factual claims MUST include citations that reference specific verbatim source segments.
- **FR-014**: Citations MUST be verifiable: each cited quote MUST be an exact substring of a canonical stored segment for the responding Spirit.
- **FR-015**: If a citation fails verification, the system MUST remove it (or repair it if possible) before delivering the response.
- **FR-016**: The system MUST include a machine-readable representation of citation data in addition to any human-visible citation markers. Marker style is adapter-owned and implementation-defined per platform.

#### Archive Publication (Ingested Content → Archive Rooms)

- **FR-017**: When new content is ingested for a Spirit, the system MUST publish it to the Spirit’s Archive Room in a way that is safe to retry without duplicates.
- **FR-018**: If publication fails partway through a source thread, retries MUST resume posting remaining content without duplicating already-published segments.

#### Voice Calls (Dialogue Rooms)

- **FR-019**: The system MUST support 1:1 voice calls between a user and a Spirit in a Dialogue Room.
- **FR-020**: Voice interactions MUST preserve the grounding principle: the Spirit’s spoken responses MUST be derived from grounded text reasoning and MUST result in citations.
- **FR-021**: For each Spirit voice turn, the system MUST post a text transcript of the spoken content to the same Dialogue Room (optionally as a thread), with citations. Voice transcripts are sourced from Gemini Live’s built-in transcription streams.
- **FR-022**: For MVP, the system MUST power Spirit voice interactions using Gemini Live.
- **FR-023**: The system MUST gracefully handle voice failures (disconnections, temporary unavailability) by notifying the user in the room and leaving text chat functional.

#### Audit & Safety

- **FR-024**: The system MUST retain an audit trail of Dialogue Room conversations (text and voice transcripts) with associated citations for later review and debugging.
- **FR-025**: The system MUST protect secrets and user-provided credentials from being emitted in logs, transcripts, or citations.

### Acceptance Coverage

- **FR-004–FR-007, FR-017–FR-018**: Demonstrated by User Story 2 acceptance scenarios.
- **FR-007a, FR-008–FR-016, FR-024–FR-025**: Demonstrated by User Story 1 acceptance scenarios (including Matrix adapter integration tests for appservice auth).
- **FR-019–FR-023**: Demonstrated by User Story 3 acceptance scenarios.

### Key Entities *(include if feature involves data)*

- **Spirit**: A platform-managed AI persona that speaks in-character and cites only from its own memory.
- **User**: A real human participant in Matrix.
- **Archive Room**: A public, read-only, ingestion-backed room for a Spirit; non-interactive (no AI). Per source, a thread root summarizes the source (from ingestion / EverMemOS metadata) and replies contain ordered verbatim transcript excerpts.
- **Dialogue Room**: A private room used for interactive conversation with one or more Spirits; supports text and may support voice calls.
- **Source**: An upstream content item ingested for a Spirit (video, book, podcast, document).
- **Segment**: A verbatim excerpt of a Source used for retrieval, citations, and Archive Room posting.
- **Citation**: A structured reference to a Segment (source title, URL, quote, and optional location context).
- **Voice Session**: A time-bounded voice interaction in a Dialogue Room, producing audio plus a text transcript with citations.
- **Platform Adapter**: The integration layer that maps a platform’s native events and rooms to the platform-agnostic conversation interface.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Users receive a grounded, cited Spirit text response within 5 seconds for at least 90% of messages that have relevant evidence available.
- **SC-002**: 100% of citations delivered in Spirit responses are verifiable (quoted text is a substring of canonical stored segments for that Spirit).
- **SC-003**: Spirits generate zero AI responses in Archive Rooms across all test scenarios (100% enforcement).
- **SC-004**: In a test suite of multi-Spirit Dialogue Rooms, cross-Spirit citation leakage occurs in 0% of Spirit responses.
- **SC-005**: In 1:1 voice calls, median latency from end-of-user-utterance to start-of-Spirit-speech is under 3 seconds in a controlled test environment.
- **SC-006**: 100% of Spirit voice turns produce a corresponding text transcript entry with citations in the same Dialogue Room.
- **SC-007**: The system supports at least 50 concurrent active Dialogue Rooms (text and/or voice) while maintaining success criteria SC-001 and SC-005.

## Scope & Boundaries

### In Scope (MVP)

- Matrix + Element as the primary user experience surface.
- Archive Rooms + Dialogue Rooms and their behavioral enforcement.
- Grounded Spirit text chat in Dialogue Rooms with verifiable citations.
- 1:1 Spirit voice calls in Dialogue Rooms with transcript + citations.
- Archive publication of ingested content as source threads with ordered segments.
- Platform-agnostic core logic that can be reused by additional messaging platforms.

### Out of Scope (MVP)

- Multi-Spirit voice discussions and explicit floor-control behavior in group calls.
- End-to-end encrypted voice calls.
- Federation with external Matrix homeservers.
- Spirit-generated content in any public room (Archive Rooms remain verbatim-only).

## Assumptions

- A Spirit’s memory is pre-populated by ingestion pipelines; the chat experience depends on available ingested content.
- A Spirit’s identity is distinct and stable across time; citations and Archive content remain attributable to a single Spirit.
- Voice calls are acceptable without end-to-end encryption for MVP demonstration purposes.

## Dependencies

- A Matrix homeserver and Element client environment suitable for Bibliotalk users.
- An ingestion pipeline capable of producing canonical source segments for citations and Archive publication.
- Availability of Gemini Live for voice interactions.
- The Matrix adapter (`matrix_service`) is implemented in Node.js/TypeScript using `matrix-js-sdk` (chosen for ecosystem alignment and maintenance posture).
