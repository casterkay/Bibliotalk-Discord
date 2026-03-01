# Quickstart: Agent Service

**Feature**: 001-agent-service
**Prerequisites**: Python 3.11+, Node.js 20+ (for voice sidecar)

## 1. Setup

```bash
# Clone and enter the project
cd Bibliotalk

# Create virtual environment
python -m venv .venv
source .venv/bin/activate

# Install dependencies
pip install -e ".[dev]"  # or: uv sync

# Copy environment template
cp .env.example .env
# Edit .env with your API keys:
#   GOOGLE_API_KEY=...          (Gemini API)
#   SUPABASE_URL=...
#   SUPABASE_SERVICE_ROLE_KEY=...
#   EMOS_BASE_URL=...
```

## 2. Quick Test (CLI Harness)

The fastest way to test a Clone agent — no Matrix/Synapse required:

```bash
# Start a CLI chat with a Clone (uses mock EMOS data)
python -m bt_cli --agent confucius --mock-emos

# Start with real EMOS instance
python -m bt_cli --agent confucius
```

Example session:
```
> What did you say about learning?
Confucius (Clone): The pursuit of learning is endless.
As I once reflected, "Learning without thought is labor
lost; thought without learning is perilous."¹

──────────
Sources:
[1] The Analects, Book II — gutenberg:3330
```

## 3. Run Tests

```bash
# Unit tests (no external services needed)
pytest tests/unit/ -v

# Contract tests (EMOS client mock validation)
pytest tests/contract/ -v

# Integration tests (requires Docker Compose for EMOS)
docker compose -f docker-compose.test.yml up -d
pytest tests/integration/ -v -m integration
docker compose -f docker-compose.test.yml down
```

## 4. Start the Full Service (with Matrix)

```bash
# Ensure Synapse is running and appservice is registered
# Start bt_agent
uvicorn bt_agent.main:app --host 0.0.0.0 --port 8009

# Start bt_voice_sidecar (for voice calls)
cd bt_voice_sidecar && npm start
```

## 5. Verify

1. Open Element, log into `bibliotalk.space`
2. Start a DM with `@bt_confucius_clone:bibliotalk.space`
3. Send: "What is the meaning of virtue?"
4. Clone should respond with grounded citations

## Project Structure

```
bt_common/                  # Shared Python library
├── emos_client.py          # Async EMOS HTTP client
├── citation.py             # Citation models + validation
├── segment.py              # Segment models + BM25 re-ranking
└── matrix_helpers.py       # Message formatting

bt_agent/                   # Core agent service
├── main.py                 # FastAPI appservice entry point
├── appservice.py           # Matrix event handler (mautrix)
├── agent_factory.py        # ADK agent creation
├── tools/
│   ├── memory_search.py    # EMOS retrieve + re-rank
│   └── emit_citations.py   # Citation attachment
├── voice/
│   ├── session_manager.py  # Voice session lifecycle
│   └── backends/
│       ├── base.py         # VoiceBackend ABC
│       ├── nova_sonic.py   # Nova Sonic backend
│       └── gemini_live.py  # Gemini Live backend
└── discussion/
    ├── orchestrator.py     # Multi-agent LoopAgent
    └── a2a_server.py       # Per-Clone A2A endpoint

bt_voice_sidecar/           # Node.js voice bridge
├── index.js                # Entry point
├── matrixrtc.js            # MatrixRTC client
└── audio_bridge.js         # WebSocket bridge to bt_agent

bt_cli/                     # CLI test harness
└── __main__.py             # stdin/stdout Clone chat

tests/
├── unit/                   # No external deps
├── contract/               # Mock HTTP responses
└── integration/            # Docker Compose + real services
```
