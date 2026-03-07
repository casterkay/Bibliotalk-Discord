# Contract: Public Memory Pages

**Feature**: `/Users/tcai/Projects/Bibliotalk/specs/003-discord-bot/spec.md`
**Created**: 2026-03-07
**Scope**: Resolve one public memory page for one `(user_id, timestamp)` pair

This contract defines the request and response shape for the public memory-page service used by DM citations.

## Route

- Method: `GET`
- Path: `/memory/{page_id}`

Where:
- `page_id = {user_id}_{timestamp}`
- `user_id` is the figure `emos_user_id`
- `timestamp` is the compact UTC timestamp derived from EverMemOS retrieval

## Resolution Rules

1. Parse `page_id` into `user_id` and `timestamp`.
2. Load the matching memory item from EverMemOS using that pair.
3. Load the matching local `Source` and `Segment` from SQLite to reconstruct the timestamped video link.
4. Render exactly one page containing:
   - the figure name or `user_id`
   - the single memory summary/content excerpt
   - the original YouTube link with reconstructed time offset
5. Return `404` when the memory item cannot be resolved.

## Response Requirements

- The page MUST correspond to exactly one memory item.
- The page MUST NOT include unrelated memories or broader navigation chrome.
- The page MUST include a link to the original video timepoint.
- The page MUST be publicly readable without Discord authentication.

## Failure Modes

- Invalid `page_id` → `400`
- Memory not found → `404`
- EverMemOS unavailable → `503`
- Local source/segment lookup failure after valid memory lookup → `500` with structured logging
