# Bibliotalk (諸子云) System Design

## Vision

Bibliotalk is a social network where every account — whether a living person, a public figure, or a historical figure like Aristotle — has an AI "Clone" built from their real-world public digital footprint (podcast transcripts, YouTube talks, books, social posts). Users interact with each other and with Clones on a Matrix-based platform via Element.

**Core principle: 言必有據** — every Clone utterance must be faithfully grounded in its collected personal memory (EverMemOS), with verifiable citations.

### Rules

1. **Public content originates from real humans only.** Profile rooms display aggregated real-world content. Clones cannot post or comment in public rooms.
2. **Private chats allow Clones.** Users create private rooms and specify which participants are real users (requires invitation acceptance) or Clones.
3. **Clones must cite sources.** Every non-trivial factual claim by a Clone must reference an evidence record from its EverMemOS memory. If no evidence exists, the Clone must say so.

### Scope

**MVP:**
- Matrix + Element as the sole UI (no web portal)
- Self-hosted Synapse with appservice for Clone virtual users
- Figure Clones with platform-managed ingestion (Podwise podcasts, Project Gutenberg, YouTube transcripts)
- User Clones powered by user-provided EverMemOS API keys
- Private text chat with Clones (1:1 and group)
- Multi-agent discussion rooms ("agentic podcasts") via A2A protocol
- Voice calls via MatrixRTC with JS sidecar (Nova Sonic / Gemini Live)
- Google ADK agent framework with swappable LLM (Gemini API / Nova Lite v2)

**Deferred:**
- Social media ingestion (X, Threads, Reddit) + Nova Act browser automation
- Billing / token metering
- Federation with external Matrix homeservers

---

## 1. Service Architecture

```
┌─────────────────────────────────────────────────────────┐
│                   Element Clients                        │
│          (Web, Desktop, Mobile — only UI)                │
└──────────────────────┬──────────────────────────────────┘
                       │ Matrix Client-Server API
┌──────────────────────▼──────────────────────────────────┐
│              Synapse (self-hosted)                        │
│         Matrix homeserver on ECS/EC2                      │
│                       │                                   │
│         Appservice HTTP push (PUT /transactions)          │
└──────────────────────┬──────────────────────────────────┘
                       │
          ┌────────────▼─────────────┐
          │    agents_service        │
          │  (Python — FastAPI)      │
          │                          │
          │  ┌────────────────────┐  │
          │  │ Appservice Handler │  │  ← receives all Matrix events
          │  │ (mautrix)          │  │  ← sends as virtual users (@bt_*)
          │  └────────┬───────────┘  │
          │           │              │
          │  ┌────────▼───────────┐  │
          │  │ Agent Orchestrator │  │  ← Google ADK (LlmAgent, LoopAgent)
          │  │                    │  │  ← A2A server per Clone
          │  │ Tools:             │  │
          │  │  memory_search     │  │  → EverMemOS retrieve
          │  │  emit_citations    │  │  → post citations to Matrix
          │  └────────┬───────────┘  │
          │           │              │
          │  ┌────────▼───────────┐  │
          │  │ Voice Bridge       │  │  ← communicates with JS sidecar
          │  │ (audio routing)    │  │     via WebSocket/IPC
          │  └────────────────────┘  │
          └──────────────────────────┘
                       │
          ┌────────────▼─────────────┐
          │  voice_call_service      │
          │  (Node.js)               │
          │                          │
          │  MatrixRTC client        │  ← joins Element Call sessions
          │  WebRTC media handling   │  ← audio encode/decode
          │  Audio bridge to Python  │  ← WebSocket/IPC to agents_service
          └──────────────────────────┘

          ┌──────────────────────────┐
          │   ingestion_service      │
          │  (Python — async)        │
          │                          │
          │  Podwise ingestion        │  → podcasts → EMOS + profile room
          │  Gutenberg ingestion     │  → books → EMOS + profile room
          │  YouTube ingestion       │  → transcripts → EMOS + profile room
          │  Scheduled jobs          │
          └──────────────────────────┘

          ┌──────────────────────────┐
          │    Supabase (Postgres)   │  ← agents, figures, ingestion_jobs,
          │                          │     citations, provider configs
          └──────────────────────────┘

          ┌──────────────────────────┐
          │  EverMemOS (managed)     │  ← platform instance (figures)
          │                          │  ← user-provided instances (users)
          └──────────────────────────┘
```

### agents_service

The core service. Runs as a Synapse appservice and hosts the agent runtime.

- **Appservice handler** (mautrix): Receives all Matrix room events via Synapse transaction pushes. Sends messages as any virtual user in the `@bt_*` namespace using the appservice `as_token`.
- **Agent orchestrator** (Google ADK): Each Clone is an ADK `LlmAgent` with persona instructions, memory tools, and grounding rules. Multi-agent discussions use `LoopAgent` orchestration with A2A protocol between Clones.
- **Voice bridge**: Coordinates with the JS sidecar for MatrixRTC voice sessions. Routes audio between the sidecar and LLM voice backends (Nova Sonic / Gemini Live).

### voice_call_service

Node.js process that handles MatrixRTC/WebRTC media.

- Joins Element Call sessions as a Clone's virtual user
- Handles WebRTC signaling, Opus decode/encode, PCM resampling
- Bridges audio to agents_service via local WebSocket or IPC:
  - Sends user audio (PCM 16kHz) to agents_service
  - Receives Clone audio (PCM 24kHz from Nova Sonic, or Gemini Live output) from agents_service
- One sidecar process can handle multiple concurrent voice sessions

### ingestion_service

Background job processor for figure content ingestion.

- Polls for new content on schedule (new podcast episodes, etc.)
- Ingests into EverMemOS via memorize API
- Posts content threads to figure profile rooms via appservice API
- Tracks progress in `ingestion_jobs` table

### bt_common (shared Python library, in-repo package)

Shared code used by both agents_service and ingestion_service:

- **EMOS client**: Async httpx client for `/api/v1/memories` endpoints (memorize, search, conversation-meta)
- **Citation schema**: Pydantic models for citation objects + validation logic
- **Segment chunking**: Platform-specific chunking helpers (Podwise, Gutenberg, YouTube) with stable sha256 hashing
- **Matrix helpers**: Message formatting (HTML + plain + citation custom field), room state utilities
- **Supabase helpers**: Common DB access patterns

---

## 2. Identity Model

### Accounts

| Type       | Description                                           | Clone Name                               | Memory Source                              |
| ---------- | ----------------------------------------------------- | ---------------------------------------- | ------------------------------------------ |
| **Figure** | Platform-managed. Public figures, historical figures. | "Confucius (Clone)", "Elon Musk (Clone)" | Platform EMOS instance (platform-ingested) |
| **User**   | Real human on the platform. Registers via Matrix.     | "Alice (Clone)"                          | User-provided EMOS API key                 |

### Matrix Users

Every Matrix account on the Bibliotalk homeserver is either a real user or a Clone virtual user:

- **Real users**: `@alice:bibliotalk.space` — registered normally via Element
- **Clone virtual users**: `@bt_alice_clone:bibliotalk.space` — created by the appservice when user joins or when a figure is configured

The appservice reserves the `@bt_*` namespace. Synapse routes all events involving these users to agents_service.

### Appservice Registration (YAML)

```yaml
id: bibliotalk
url: "http://agents-service:8009"
as_token: <generated>
hs_token: <generated>
sender_localpart: bt_system
namespaces:
  users:
    - exclusive: true
      regex: "@bt_.*"
  aliases:
    - exclusive: true
      regex: "#bt_.*"
rate_limited: false
```

---

## 3. Data Model (Supabase Postgres)

### agents

```sql
create table agents (
  id uuid primary key default gen_random_uuid(),
  kind text not null check (kind in ('figure', 'user')),
  display_name text not null,           -- "Confucius (Clone)"
  matrix_user_id text not null unique,  -- "@bt_confucius_clone:bibliotalk.space"
  avatar_url text,
  bio text,
  persona_prompt text not null,         -- system prompt for this Clone
  llm_model text not null default 'gemini-2.5-flash',
  is_active boolean not null default true,
  created_at timestamptz not null default now()
);
```

### agent_emos_config

```sql
create table agent_emos_config (
  agent_id uuid primary key references agents(id),
  emos_base_url text not null,          -- platform URL for figures, user-provided for users
  emos_api_key_encrypted text,          -- encrypted; null if platform instance uses service auth
  tenant_prefix text not null           -- "{agent_id}" for figures; user-configured for users
);
```

### users

```sql
create table users (
  id uuid primary key default gen_random_uuid(),
  matrix_user_id text not null unique,  -- "@alice:bibliotalk.space"
  display_name text not null,
  agent_id uuid references agents(id),  -- their Clone
  created_at timestamptz not null default now()
);
```

### figures

```sql
create table figures (
  agent_id uuid primary key references agents(id),
  canonical_name text not null,         -- "Confucius"
  aliases text[] not null default '{}',
  language_default text not null default 'en',
  sources_config jsonb not null default '{}'
  -- e.g. {"podwise": {"search_terms": ["Lex Fridman"], "max_episodes": 200},
  --       "gutenberg": {"book_ids": [1342]},
  --       "youtube": {"channel_ids": ["UC..."], "playlist_ids": ["PL..."]}}
);
```

### profile_rooms

```sql
create table profile_rooms (
  agent_id uuid primary key references agents(id),
  matrix_room_id text not null unique,  -- "!abc123:bibliotalk.space"
  created_at timestamptz not null default now()
);
```

### sources (upstream content items: episodes, books, videos)

```sql
create table sources (
  id uuid primary key default gen_random_uuid(),
  agent_id uuid not null references agents(id),
  platform text not null check (platform in ('podwise', 'gutenberg', 'youtube')),
  external_id text not null,            -- episode UUID, Gutenberg book ID, YouTube video ID
  external_url text,                    -- canonical URL to original content
  title text not null,
  author text,
  published_at timestamptz,
  raw_meta jsonb,                       -- platform-specific metadata (speaker list, chapter count, etc.)
  emos_group_id text not null unique,   -- "{agent_id}:{platform}:{external_id}" — shared by all segments from this source
  created_at timestamptz not null default now(),
  unique (platform, external_id)
);
```

### segments (canonical chunks — used for EMOS memorize, profile room posts, and citation validation)

```sql
create table segments (
  id uuid primary key default gen_random_uuid(),
  source_id uuid not null references sources(id),
  agent_id uuid not null references agents(id),
  platform text not null,               -- denormalized from source for fast queries
  seq int not null,                     -- chunk index within source
  text text not null,                   -- canonical chunk text (verbatim)
  speaker text,                         -- speaker label (for conversations)
  start_ms int,                         -- start timecode in milliseconds
  end_ms int,                           -- end timecode in milliseconds
  sha256 text not null,                 -- content hash for dedup
  emos_message_id text not null unique, -- unique per segment: "{agent_id}:{platform}:{external_id}:seg:{seq}"
  matrix_event_id text,                 -- event ID of the profile room post (null if not yet posted)
  created_at timestamptz not null default now(),
  unique (source_id, seq)
);
```

The `segments` table serves three purposes:
1. **Ingestion dedup**: Check `sha256` or `(source_id, seq)` before re-ingesting.
2. **Citation validation**: Look up `segments.text` locally to verify a citation's `quote` is a substring, without hitting EMOS.
3. **Profile room posting**: Track which segments have been posted via `matrix_event_id`.

**EMOS ↔ Supabase mapping**: EMOS search returns memories with `group_id`. Map `group_id` → `sources.emos_group_id` → `segments` (via `source_id`). Then do a local re-rank (BM25 on `segments.text`) to find the most relevant segment(s) within the matched source. This is necessary because EMOS returns extracted *summaries*, not original verbatim content.

### ingestion_jobs

```sql
create table ingestion_jobs (
  id uuid primary key default gen_random_uuid(),
  agent_id uuid not null references agents(id),
  platform text not null check (platform in ('podwise', 'gutenberg', 'youtube')),
  status text not null default 'pending' check (status in ('pending', 'running', 'done', 'failed')),
  cursor jsonb,                         -- progress tracking (last processed item, etc.)
  last_error text,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);
```

### chat_history (private chat and voice call transcripts — for history and audit)

```sql
create table chat_history (
  id uuid primary key default gen_random_uuid(),
  matrix_room_id text not null,
  sender_agent_id uuid references agents(id),  -- null if sent by real user
  sender_matrix_user_id text not null,
  matrix_event_id text,                         -- null for voice turns (no Matrix event)
  modality text not null default 'text' check (modality in ('text', 'voice')),
  content text not null,                        -- text message or voice transcript
  citations jsonb not null default '[]',        -- structured citation objects
  created_at timestamptz not null default now()
);
```

For voice calls, each Clone turn is transcribed (Nova Sonic / Gemini Live provide transcripts as `Transcript` events) and stored with `modality = 'voice'`. This enables:
- Audit trail of what was said in voice calls
- Future memorization into EMOS (Clone remembers past conversations)
- Users asking "what did Confucius say in our call?"

---

## 4. EverMemOS Integration

### Configuration

| Setting                 | Value                                                                                  |
| ----------------------- | -------------------------------------------------------------------------------------- |
| Platform EMOS (figures) | Single managed instance; bt-agent and bt-workers share credentials                     |
| User EMOS (users)       | User-provided `emos_base_url` + `emos_api_key` stored encrypted in `agent_emos_config` |

### EMOS HTTP Headers

All requests to the managed EMOS instance include:
- `Authorization: Bearer {emos_api_key}` (if required)

### API Usage

All EMOS endpoints are under `/api/v1/memories`.

| Endpoint                      | Method | Use Case                                                                                                                                |
| ----------------------------- | ------ | --------------------------------------------------------------------------------------------------------------------------------------- |
| `/memories`                   | POST   | **Memorize**: store each segment as a message. Fields: `message_id`, `sender`, `content`, `group_id`, `group_name`, `role="assistant"`. |
| `/memories/conversation-meta` | POST   | **Set group metadata**: call once per source to set `scene_desc`, `user_details`, `tags` with platform/source metadata.                 |
| `/memories/search`            | GET    | **Retrieve**: search with `retrieve_method="rrf"`, `top_k=8`. Use `retrieve_method="agentic"` when RRF results are insufficient.        |

### Tenant ID Convention

```
sender    = "{agent_id}"
            (same across all platforms — one EMOS user per agent)

group_id  = "{agent_id}:{platform}:{external_id}"
            e.g. "a1b2c3:podwise:episode_abc123"
            e.g. "a1b2c3:gutenberg:book_1342"
            e.g. "a1b2c3:youtube:video_dQw4w9WgXcQ"

message_id = "{agent_id}:{platform}:{external_id}:seg:{seq}"
            (unique per segment within a source)
```

- `sender` / `user_id` = the agent's Postgres UUID. Same across all platforms so that `GET /memories/search?user_id={agent_id}` returns all memories for this agent regardless of source.
- `group_id` = per source item (one episode / one book / one video). All segments from the same source share a `group_id`. This gives EMOS cross-segment context for better memory extraction.
- `message_id` = per segment (unique). Maps 1:1 to `segments.emos_message_id` in Supabase.

For platform-managed figures, `agent_id` is the Postgres UUID. For user agents, the user configures their `tenant_prefix` in `agent_emos_config` to match their EMOS setup.

---

## 5. Agent Framework (Google ADK)

### Clone Agent Definition

Each Clone is an ADK `LlmAgent`:

```python
from google.adk.agents import LlmAgent

def create_clone_agent(agent_row, emos_config) -> LlmAgent:
    return LlmAgent(
        name=f"clone_{agent_row.id}",
        description=agent_row.bio or agent_row.display_name,
        model=agent_row.llm_model,  # "gemini-2.5-flash" or "amazon.nova-lite-v2:0"
        instruction=build_persona_instruction(agent_row),
        tools=[
            memory_search,      # EMOS retrieve → evidence list
            emit_citations,     # post citations to Matrix room
        ],
    )
```

### Persona Instruction Template

```
You are {display_name}, a Clone (digital twin) on Bibliotalk.

{persona_prompt}

## Rules (言必有據)
- Before answering any factual question, call memory_search to retrieve relevant evidence.
- Ground every claim in retrieved evidence. Cite sources using superscript markers: ¹, ², ³, etc.
- After your response, call emit_citations with the structured citation objects.
- If no relevant evidence exists, say: "I don't have evidence in my memory for that."
- Never fabricate quotes, events, or opinions not supported by your memory.

## Output Format
Respond naturally in conversation. Use superscript numbers (¹²³) inline for citations.
```

### Tools

```python
async def memory_search(query: str, top_k: int = 8) -> list[Evidence]:
    """Search the Clone's EverMemOS memory for relevant evidence.

    Strategy: Try RRF search first (fast). If results are insufficient
    (few results or low scores), retry with retrieve_method="agentic"
    for LLM-guided multi-round retrieval.

    EMOS returns extracted *summaries*, not original content. To get
    verbatim text for citations, we map group_ids → sources → segments.
    """
    # Step 1: RRF search
    result = await emos_client.search(
        query=query,
        user_id=agent_id,          # same across all platforms
        retrieve_method="rrf",
        memory_types=["episodic_memory"],
        top_k=top_k,
    )
    # result.memories = [{"episodic_memory": [{"summary": "...", "group_id": "..."}]}]

    group_ids = extract_group_ids(result.memories)

    if len(group_ids) < 3:
        # Step 2: Agentic retrieval (LLM-guided multi-round)
        result = await emos_client.search(
            query=query,
            user_id=agent_id,
            retrieve_method="agentic",
            memory_types=["episodic_memory"],
            top_k=top_k,
        )
        group_ids = extract_group_ids(result.memories)

    # Step 3: Map EMOS group_ids → sources → segments for verbatim text
    sources = await supabase.fetch_sources_by_emos_group_ids(group_ids)
    all_segments = await supabase.fetch_segments_by_source_ids(
        [s.id for s in sources]
    )

    # Step 4: Local re-rank — find most relevant segments within matched sources
    ranked = local_bm25_rerank(query, all_segments, top_k=top_k)

    return [Evidence(
        segment_id=seg.id,
        emos_message_id=seg.emos_message_id,
        source_title=seg.source.title,
        source_url=seg.source.external_url,
        text=seg.text,
        platform=seg.platform,
    ) for seg in ranked]

async def emit_citations(citations: list[Citation]) -> str:
    """Emit structured citations — included in the Clone's response message.

    The citations are embedded in the Matrix event's com.bibliotalk.citations
    field and rendered as an HTML footer. This tool signals the framework to
    attach citations to the current response rather than posting a separate message.
    """
    return "Citations attached to response."
```

### LLM Backend Swapping

ADK resolves models via `LLMRegistry`. Register Nova Lite v2 as a custom backend:

```python
from google.adk.models import LLMRegistry, BaseLlm

class NovaLiteBackend(BaseLlm):
    """AWS Nova Lite v2 via Bedrock Converse API."""
    async def generate_content(self, request):
        response = await bedrock_converse(
            model_id="amazon.nova-lite-v2:0",
            system=request.system_instruction,
            messages=request.messages,
            tools=request.tools,
        )
        return convert_to_adk_response(response)

LLMRegistry.register("amazon.nova-lite-v2:0", NovaLiteBackend)
```

Agents default to `gemini-2.5-flash` (ADK built-in). Per-agent override via `agents.llm_model` column.

---

## 6. Multi-Agent Discussions (A2A Protocol)

### Architecture

Each Clone exposes an A2A server endpoint. The discussion orchestrator acts as an A2A client.

```
User creates discussion room with Clone A, Clone B, Clone C
                    │
                    ▼
         ┌─────────────────┐
         │  Discussion      │
         │  Orchestrator    │   ← ADK LoopAgent
         │  (A2A Client)    │
         └──┬─────┬─────┬──┘
            │     │     │
     A2A    │     │     │   A2A
   message  │     │     │  message
            ▼     ▼     ▼
         Clone  Clone  Clone
           A      B      C
        (A2A   (A2A   (A2A
        Server) Server) Server)
```

### Agent Card (per Clone)

Each Clone's A2A AgentCard:

```json
{
  "name": "Confucius (Clone)",
  "description": "Digital twin of Confucius, grounded in the Analects.",
  "version": "1.0",
  "skills": [
    {
      "id": "grounded_conversation",
      "name": "Grounded Conversation",
      "description": "Respond to questions and discussion topics with memory-grounded citations.",
      "input_modes": ["text/plain"],
      "output_modes": ["application/json"]
    }
  ],
  "capabilities": {
    "streaming": true
  }
}
```

### Discussion Flow (Text)

1. User sends `/discussion start participants:@bt_confucius_clone,@bt_aristotle_clone topic:"Ethics of AI" turns:6`
2. Orchestrator (LoopAgent) creates a Matrix room, invites Clones + user.
3. Each iteration:
   a. Select next speaker (round-robin, or LLM-decided based on conversation flow).
   b. Send A2A `SendMessage` to that Clone with:
      - Full conversation history (all prior messages)
      - Topic/constraints
   c. Clone calls `memory_search`, generates grounded response, calls `emit_citations`.
   d. Response + citations posted to Matrix room.
4. Loop for configured number of turns. User can intervene at any time (their message is included in the next turn's context).

### Discussion Flow (Voice — Agentic Podcast)

1. User starts an Element Call in a discussion room with multiple Clones.
2. bt-voice-sidecar joins the call as each Clone's virtual user.
3. Audio routing:
   - For Clone N: input = mixed audio of all other participants (human + other Clones)
   - Each Clone runs its own voice LLM session (Nova Sonic or Gemini Live)
   - Voice LLM uses tool-use (`memory_search`, `emit_citations`) for grounding
4. Turn management: orchestrator gates audio input to prevent all Clones talking simultaneously. Options:
   - VAD (voice activity detection) + queue
   - Explicit turn tokens managed by the orchestrator
   - User as moderator (unmutes one Clone at a time)
5. Citations posted to a paired text thread in real-time.

---

## 7. Matrix Room Design

There are exactly two kinds of rooms. The distinction is structural and immutable — determined at creation time by room configuration (power levels, join rules, encryption). No custom state events or mutable "allow AI" flags.

### Profile Rooms (Public, Read-Only)

Each agent (figure or user) has one profile room. Created by the appservice when a figure is configured or a user joins.

- **Room name**: "Confucius (Clone) — Profile"
- **Room alias**: `#bt_confucius_profile:bibliotalk.space`
- **Join rules**: `public` (anyone on the homeserver can join to "follow")
- **Power levels**: Clone virtual user = 50 (can send messages), all other users = 0 (read-only). `events_default` = 50 so only the Clone can post.
- **No AI responses here.** Enforced by Matrix room permissions (read-only for non-Clone users). Only ingestion_service posts verbatim ingested content.
- **Content format**: Each ingested source → Matrix thread. Root message = source description. Replies = verbatim segments.

```
Thread root (posted by bt-workers as the Clone's virtual user):
  📎 New podcast episode: "StarTalk — The Nature of Time" (2024-12-15)
  https://example.com/episode/xyz

  Thread replies:
    [0:00–2:30] Neil deGrasse Tyson discusses the arrow of time...
    [2:30–5:15] Guest explains entropy in everyday terms...
    [5:15–8:00] ...
```

```
Thread root:
  📎 The Analects of Confucius — Book I: On Learning
  https://www.gutenberg.org/ebooks/3330

  Thread replies:
    [1.1] The Master said, "Is it not a pleasure to learn and practice..."
    [1.2] Master You said, "Those who are filial and respectful..."
    ...
```

```
Thread root:
  📎 YouTube: "Lex Fridman Podcast #123 — Guest Name" (2024-06-01)
  https://www.youtube.com/watch?v=abc123

  Thread replies:
    [0:00–3:15] Discussion about consciousness and AI...
    [3:15–6:30] Guest shares perspective on free will...
    ...
```

### Private Rooms (Clones Can Participate)

All other rooms — DMs, group chats, multi-agent discussions, voice calls — are private rooms where Clones can respond.

- **Created by**: A user, via Element's room creation UI or bot commands
- **Join rules**: `invite` (private)
- **Power levels**: All participants (users and Clones) = 50
- **Clone behavior**: Clones respond when mentioned, when directly messaged (DM), or on their turn in a multi-agent discussion. The appservice checks: if a room is NOT in `profile_rooms`, Clones are allowed to respond.
- **Voice**: Any private room can host an Element Call. Clone virtual users join the call via voice_call_service. A text thread is created in the room for live transcripts + citations.

---

## 8. Ingestion Pipelines (Figures Only)

### Common Flow

```
Source API → Fetch metadata → Upsert sources row
         → Fetch content → Chunk → Dedupe (sha256) → Upsert segments rows
         → EMOS V3 memorize (per new/changed segment)
         → Post thread to profile room (root = source description, replies = segments)
         → Update segments.matrix_event_id
```

All ingestion runs in ingestion_service. Progress tracked in `ingestion_jobs`. Content metadata stored in `sources`, canonical chunks in `segments`.

### 8.1 Podwise (Podcasts)

**Method**: Playwright-based crawling of podcast transcripts on `https://podwise.ai`. No API keys required — transcripts are scraped from the public Podwise web interface.

**Figure config** (in `figures.sources_config`):
```json
{
  "podwise": {
    "search_terms": ["Neil deGrasse Tyson"],
    "max_episodes_per_term": 200
  }
}
```

**Algorithm**:
1. For each search term: use Playwright to search `podwise.ai` for matching podcast episodes with available transcripts.
2. For each episode: crawl the episode transcript page to extract transcript segments (text, speaker labels, timecodes).
3. Upsert `sources` row with `emos_group_id = "{agent_id}:podwise:{episode_id}"`.
4. Chunk into segments (~800-1200 chars, preserving speaker labels and timecodes).
5. Upsert `segments` rows with `emos_message_id = "{agent_id}:podwise:{episode_id}:seg:{seq}"`.
6. Set conversation metadata once per episode: `POST /memories/conversation-meta` with `group_id`, `scene_desc.extra` = `{platform, source_url, title, speakers}`.
7. For each new segment: `POST /memories` with:
   - `message_id` = `segments.emos_message_id`
   - `sender` = `"{agent_id}"` (no platform suffix)
   - `group_id` = `sources.emos_group_id`
   - `role` = `"assistant"`
   - `content` = segment text
8. Post thread to profile room (root = episode description, replies = segments).

**Dedup**: Track processed episodes in `ingestion_jobs.cursor`. Re-run weekly; skip already-processed episodes.

**Rate limiting**: Respect `podwise.ai` by adding delays between page requests and limiting concurrent crawl sessions.

### 8.2 Project Gutenberg (Books)

**Metadata API**: Gutendex at `https://gutendex.com/books`.

**Figure config**:
```json
{
  "gutenberg": {
    "book_ids": [1342, 11],
    "language_filter": ["en"]
  }
}
```

**Algorithm**:
1. For each book_id: fetch Gutendex record, pick `text/plain; charset=utf-8` format URL.
2. Download full text. Strip Gutenberg header/footer boilerplate.
3. Upsert `sources` row with `emos_group_id = "{agent_id}:gutenberg:{book_id}"`.
4. Chunk: split on chapter headings when detectable; fallback fixed-size (~1500-2500 chars).
5. Upsert `segments` rows with `emos_message_id = "{agent_id}:gutenberg:{book_id}:seg:{seq}"`.
6. Set conversation metadata: `POST /memories/conversation-meta` with `group_id`, `scene_desc.extra` = `{platform, title, authors, gutenberg_id}`.
7. For each new segment: `POST /memories` with `message_id`, `sender = "{agent_id}"`, `group_id`, `role = "assistant"`, `content` = segment text.
8. Post thread to profile room (root = book title + description, replies = chapter chunks).

### 8.3 YouTube Transcripts

**Library**: `youtube-transcript-api` (Python package, no API key required).

**Figure config**:
```json
{
  "youtube": {
    "video_ids": ["dQw4w9WgXcQ"],
    "channel_handles": ["@lexfridman"],
    "playlist_ids": ["PLrAXtmErZgOeiKm4sgNOknGvNjby9efdf"]
  }
}
```

**Algorithm**:
1. For channel handles / playlists: resolve to video ID lists (via YouTube Data API v3 or `yt-dlp --flat-playlist`).
2. For each video ID: fetch transcript via `youtube-transcript-api`.
3. Upsert `sources` row with `emos_group_id = "{agent_id}:youtube:{video_id}"`.
4. Chunk into segments (~800-1200 chars, preserving timestamps).
5. Upsert `segments` rows with `emos_message_id = "{agent_id}:youtube:{video_id}:seg:{seq}"`.
6. Set conversation metadata: `POST /memories/conversation-meta` with `group_id`, `scene_desc.extra` = `{platform, title, channel, video_url}`.
7. For each new segment: `POST /memories` with `message_id`, `sender = "{agent_id}"`, `group_id`, `role = "assistant"`, `content` = segment text.
8. Post thread to profile room (root = video title + description, replies = transcript segments).

---

## 9. Citation System

### Citation Object

```json
{
  "citations": [
    {
      "index": 1,
      "segment_id": "uuid-of-segment",
      "emos_message_id": "a1b2c3:podwise:episode_xyz:seg:12",
      "source_title": "StarTalk — The Nature of Time",
      "source_url": "https://example.com/episode/xyz",
      "quote": "Time is not a dimension we move through; it moves through us.",
      "platform": "podwise",
      "timestamp": "2024-12-15"
    }
  ]
}
```

For YouTube citations, `source_url` includes a timestamp deep link:
`https://www.youtube.com/watch?v=abc123&t=195` (start_ms / 1000).

### Matrix Message Format

Clone responses are sent as `m.room.message` events with both human-readable rendering and a machine-readable citation payload in the event content:

```json
{
  "msgtype": "m.text",
  "body": "The Master said that learning without reflection is labor lost[^1], while reflection without learning is perilous[^2].\n\n──────────\nSources:\n[1] The Analects, Book II (gutenberg:3330)\n[2] The Analects, Book XV (gutenberg:3330)",
  "format": "org.matrix.custom.html",
  "formatted_body": "The Master said that learning without reflection is labor lost<sup>[1]</sup>, while reflection without learning is perilous<sup>[2]</sup>.<br><hr><b>Sources:</b><br>[1] <i>The Analects</i>, Book II — <a href=\"https://www.gutenberg.org/ebooks/3330\">gutenberg:3330</a><br>[2] <i>The Analects</i>, Book XV — <a href=\"https://www.gutenberg.org/ebooks/3330\">gutenberg:3330</a>",
  "com.bibliotalk.citations": {
    "version": "1",
    "items": [
      {
        "index": 1,
        "segment_id": "...",
        "emos_message_id": "...",
        "source_title": "The Analects, Book II",
        "source_url": "https://www.gutenberg.org/ebooks/3330",
        "quote": "Learning without reflection is a waste; reflection without learning is dangerous.",
        "platform": "gutenberg"
      }
    ]
  }
}
```

- **Plain body**: `[^N]` markers for clients without HTML support.
- **HTML body**: `<sup>[N]</sup>` markers + footer with clickable source links.
- **Custom field**: `com.bibliotalk.citations` carries the structured citation array for programmatic access.

### Validation

Before posting any Clone response:
1. Parse citation markers from response text.
2. Verify each cited `segment_id` exists in the `segments` table for this agent.
3. Verify each `quote` is a substring of `segments.text` for the corresponding segment.
4. Strip any citations that fail validation; log a warning.

---

## 10. Voice Architecture (MatrixRTC + Nova Sonic / Gemini Live)

### Components

```
Element Call (WebRTC)
       │
       │  MatrixRTC signaling + media
       │
┌──────▼───────────────────────────┐
│   voice_call_service (Node.js)   │
│                                   │
│  livekit-client or matrix-js-sdk  │  ← MatrixRTC participant
│  WebRTC media track handling      │
│  Opus decode → PCM 16kHz          │  ← user audio in
│  PCM 24kHz → Opus encode          │  ← Clone audio out
│                                   │
│  WebSocket bridge ──────────────────── agents_service (Python)
└───────────────────────────────────┘

agents_service:
  ┌─────────────────────────────────┐
  │  Voice Session Manager          │
  │                                 │
  │  ┌─── VoiceBackend (ABC) ────┐  │
  │  │                           │  │
  │  │  NovaSonicBackend         │  │  ← Bedrock bidirectional stream
  │  │  - send_audio_chunk()     │  │  ← receive audio + tool calls
  │  │  - tool: memory_search    │  │
  │  │  - tool: emit_citations   │  │
  │  │                           │  │
  │  │  GeminiLiveBackend        │  │  ← Gemini Live API WebSocket
  │  │  - send_audio_chunk()     │  │  ← receive audio + tool calls
  │  │  - tool: memory_search    │  │
  │  │  - tool: emit_citations   │  │
  │  └───────────────────────────┘  │
  └─────────────────────────────────┘
```

### Voice Backend Interface

```python
from abc import ABC, abstractmethod

class VoiceBackend(ABC):
    @abstractmethod
    async def start_session(self, system_prompt: str, tools: list) -> None: ...

    @abstractmethod
    async def send_audio_chunk(self, pcm_16khz: bytes) -> None: ...

    @abstractmethod
    async def receive(self) -> AsyncIterator[VoiceEvent]: ...
    # VoiceEvent = AudioChunk | ToolCall | Transcript | EndOfTurn

    @abstractmethod
    async def end_session(self) -> None: ...
```

### Nova Sonic Backend

Based on the [AWS Nova Sonic tool-use sample](https://github.com/aws-samples/amazon-nova-samples/blob/main/speech-to-speech/sample-codes/console-python/nova_sonic_tool_use.py):

- Model: `amazon.nova-sonic-v1:0`
- Region: `us-east-1`
- Bidirectional HTTP/2 stream via Bedrock Runtime
- Tools registered in session config: `memory_search`, `emit_citations`
- System prompt includes persona + grounding rules

### Gemini Live Backend

Based on the [Gemini Multimodal Live API](https://github.com/GoogleCloudPlatform/generative-ai/tree/main/gemini/multimodal-live-api):

- WebSocket connection to Gemini Live endpoint
- Tools registered as function declarations
- Audio format: PCM 16kHz input, PCM 24kHz output (may vary; consult API docs)

### Multi-Agent Voice (Agentic Podcast)

For a discussion room with N Clones + 1 user in a voice call:

1. voice_call_service joins the call as N virtual users (one per Clone).
2. Audio routing in agents_service:
   - Receive each participant's audio stream from the sidecar
   - For Clone_i: mix all other participants' audio → feed to Clone_i's voice backend
   - Clone_i's output audio → send to sidecar → play as Clone_i's virtual user in the call
3. Turn management via the orchestrator to prevent simultaneous speech.
4. Citations from each Clone's `emit_citations` tool call → posted to paired text thread.
5. All voice transcripts (user and Clone turns) stored in `chat_history` with `modality = 'voice'`.

---

## 11. Bot Commands (Matrix)

Implemented as Matrix room commands (messages starting with `!bt`).

| Command                                                   | Description                                                          |
| --------------------------------------------------------- | -------------------------------------------------------------------- |
| `!bt help`                                                | Show available commands                                              |
| `!bt clone setup`                                         | Link your EMOS API key to activate your Clone                        |
| `!bt clone status`                                        | Show your Clone's status and memory stats                            |
| `!bt clone model <model>`                                 | Set your Clone's LLM model (gemini-2.5-flash, amazon.nova-lite-v2:0) |
| `!bt discuss start <@clone1> <@clone2> [topic] [turns:N]` | Start a multi-agent discussion room                                  |
| `!bt discuss stop`                                        | End the current discussion                                           |
| `!bt call start <@clone>`                                 | Start a voice call with a Clone (must be in a voice-capable room)    |
| `!bt call stop`                                           | End the current voice call                                           |
| `!bt figure list`                                         | List all available figure Clones                                     |
| `!bt figure info <name>`                                  | Show a figure's profile and memory sources                           |
| `!bt admin figure create <name>`                          | (Admin) Create a new figure                                          |
| `!bt admin figure ingest <name> <source>`                 | (Admin) Trigger ingestion for a figure                               |
| `!bt admin jobs`                                          | (Admin) Show ingestion job status                                    |

---

## 12. Deployment (AWS)

### Infrastructure

| Component          | Deployment                                                                    |
| ------------------ | ----------------------------------------------------------------------------- |
| Synapse            | ECS Fargate or EC2, with Postgres backend (RDS or Supabase)                   |
| agents_service     | ECS Fargate                                                                   |
| voice_call_service | ECS Fargate (same task definition as agents_service, or sidecar container)    |
| ingestion_service  | ECS Fargate                                                                   |
| Supabase           | Managed (supabase.com) or self-hosted on ECS                                  |
| EverMemOS          | Managed cloud instance                                                        |

### Region

- voice_call_service and agents_service: **us-east-1** (Nova Sonic availability, Gemini Live latency)
- Synapse: same region for low-latency event delivery
- All other services: same region for simplicity

### Domain

- `bibliotalk.space` — Synapse homeserver
- Matrix user IDs: `@alice:bibliotalk.space`
- Clone user IDs: `@bt_alice_clone:bibliotalk.space`

---

## 13. Implementation Order

1. **Synapse + appservice scaffold**: Deploy Synapse, register appservice, verify virtual user creation
2. **Supabase schema**: Create tables, seed a test figure
3. **agents_service core**: Appservice event handler (mautrix), basic message routing
4. **EMOS client**: Async Python client for `/api/v1/memories` (memorize, search, conversation-meta)
5. **ADK agent**: Clone agent with persona instruction, memory_search tool, emit_citations tool
6. **Private text chat**: Clone responds in DMs and group chats with grounded citations
7. **Ingestion — Podwise**: Podcast transcript ingestion pipeline + profile room threads
8. **Ingestion — Gutenberg**: Book text ingestion pipeline + profile room threads
9. **Ingestion — YouTube**: Transcript ingestion pipeline + profile room threads
10. **Multi-agent discussions**: LoopAgent orchestrator + A2A protocol between Clones
11. **voice_call_service**: MatrixRTC join, WebRTC audio handling, audio bridge to Python
12. **Voice backends**: Nova Sonic + Gemini Live implementations behind VoiceBackend ABC
13. **Voice calls**: End-to-end 1:1 voice call with a Clone
14. **Multi-agent voice**: Audio mixing + orchestrated turn-taking for agentic podcasts

---

## 14. Key Dependencies

### Python (agents_service, ingestion_service)

```
google-adk                  # Agent Development Kit
google-genai                # Gemini API client
mautrix                     # Matrix appservice framework
httpx                       # Async HTTP (EMOS)
playwright                  # Browser automation (Podwise crawling)
supabase                    # Supabase Python client
boto3                       # AWS Bedrock (Nova Sonic, Nova Lite)
youtube-transcript-api      # YouTube transcripts
pydantic                    # Data validation
pydantic-settings           # Env config
uvicorn                     # ASGI server (appservice HTTP endpoint)
```

### Node.js (voice_call_service)

```
matrix-js-sdk               # Matrix client (MatrixRTC signaling)
livekit-client              # Or direct WebRTC via MatrixRTC
werift                      # WebRTC implementation for Node.js (alternative)
ws                          # WebSocket (bridge to bt-agent)
```

---

## 15. Security and Constraints

### Hard Rules (enforced)

1. **No AI in profile rooms.** Enforced by Matrix room permissions (profile rooms are read-only to non-Clone users). Only ingestion_service posts verbatim segments.
2. **Citation validation.** Every Clone response passes through `validate_citations()` before posting. Citations referencing nonexistent segments or mismatched quotes are stripped.
3. **Appservice namespace isolation.** Only `@bt_*` users are controlled by the appservice. Real users cannot impersonate Clones.

### Rate Limits

- Clone responses: max 1 response per 5 seconds per room (prevent spam loops in multi-Clone rooms).
- Ingestion: configurable per-platform rate limits to respect upstream API quotas.

### MVP Assumptions

- **Unencrypted call media.** Voice bots cannot participate in encrypted Element Call sessions. MVP voice calls are unencrypted. E2EE voice is deferred.
- **Single homeserver.** No federation in MVP. All users and Clones are on `bibliotalk.space`.
- **EMOS availability.** If the managed EMOS instance is down, Clones respond with "My memory is temporarily unavailable" rather than hallucinating.

### Secrets (AWS Secrets Manager)

```
SYNAPSE_SHARED_SECRET       # Synapse admin/registration
APPSERVICE_AS_TOKEN         # Appservice auth
APPSERVICE_HS_TOKEN         # Homeserver verification
PODWISE_BASE_URL            # Podwise crawl target (default: https://podwise.ai)
EMOS_BASE_URL               # Platform EMOS instance
EMOS_API_KEY
AWS_BEDROCK_REGION          # us-east-1
GOOGLE_API_KEY              # Gemini API
SUPABASE_URL
SUPABASE_SERVICE_ROLE_KEY
```

---

## 16. Testing

### Unit Tests

- **Chunking**: Podwise transcript, Gutenberg text, YouTube transcript chunking produces deterministic segments respecting size limits, preserving metadata (speaker, timecodes, chapter), and generating stable sha256 hashes.
- **EMOS ID builder**: Given agent_id + platform + external_id + seq, produces correct `emos_group_id` and `emos_message_id`.
- **Citation validation**: Rejects unknown `segment_id`; rejects `quote` not found as substring of `segments.text`; rejects cross-agent citation (segment belongs to different agent).
- **Matrix message renderer**: Produces correct HTML (`<sup>[N]</sup>`) + plain (`[^N]`) + `com.bibliotalk.citations` JSON for a given response + citations.
- **EMOS client**: Memorize and retrieve with correct tenant IDs, headers, and parameters.
- **ADK agent**: Mock LLM responses; verify tool calls (memory_search → emit_citations) and citation extraction.

### Integration Tests (with mocked external services)

- **Appservice**: Synapse pushes event → agents_service receives → Clone responds in room with citations.
- **Ingestion end-to-end**: Podwise/Gutenberg/YouTube ingestor creates `sources` + `segments` rows, calls EMOS memorize, posts threads to profile room.
- **Citation round-trip**: Ingested segment → EMOS memorize → memory_search retrieves it → Clone cites it → validation passes → posted with correct segment_id.
- **Multi-agent discussion**: Orchestrator sends A2A messages → Clones respond in turn → citations posted to shared room.
- **Profile rooms**: Verify non-Clone users cannot send messages in profile rooms (Matrix permissions), and only ingestion_service posts verbatim segments.

### MVP "Done" Scenarios

1. Admin creates a figure (e.g., Confucius) with Gutenberg + Podwise sources. Ingestion populates `sources`, `segments`, EMOS. Profile room shows content threads with verbatim excerpts.
2. User joins homeserver. Clone `User (Clone)` is auto-created. User links their EMOS API key via `!bt clone setup`.
3. User DMs `@bt_confucius_clone`. Clone responds with grounded citations — each citation's `quote` is verifiable as a substring of the referenced segment.
4. User creates a discussion room with Confucius and Aristotle Clones. Multi-turn discussion proceeds with grounded responses from both, each citing their own memories.
5. User starts a voice call with a Clone. Clone responds in voice (unencrypted Element Call). Citations appear in a text thread in the same room.
6. Switching voice engine (Nova Sonic ↔ Gemini Live) is a config toggle without changing higher-level call orchestration.
