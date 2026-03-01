# Contract: A2A Clone Server

**Service**: Each Clone agent exposes an A2A server endpoint
**Protocol**: JSON-RPC 2.0 over HTTP, SSE for streaming

## Agent Card

Published at `/.well-known/agent.json` (or path-routed equivalent):

```json
{
  "name": "Confucius (Clone)",
  "description": "Digital twin of Confucius, grounded in the Analects.",
  "version": "1.0",
  "skills": [
    {
      "id": "grounded_conversation",
      "name": "Grounded Conversation",
      "description": "Respond to questions with memory-grounded citations.",
      "input_modes": ["text/plain"],
      "output_modes": ["application/json"]
    }
  ],
  "capabilities": {
    "streaming": true
  }
}
```

## Task Lifecycle

```
submitted → working → completed
                   → failed
                   → canceled
```

## Message Format (Orchestrator → Clone)

```json
{
  "jsonrpc": "2.0",
  "method": "tasks/send",
  "params": {
    "id": "task-uuid",
    "message": {
      "role": "user",
      "parts": [
        {"type": "text", "text": "conversation context + topic"}
      ]
    }
  }
}
```

## Response Format (Clone → Orchestrator)

```json
{
  "jsonrpc": "2.0",
  "result": {
    "id": "task-uuid",
    "status": {"state": "completed"},
    "artifacts": [
      {
        "parts": [
          {"type": "text", "text": "Clone's grounded response"},
          {"type": "data", "data": {"citations": [<Citation>, ...]}}
        ]
      }
    ]
  }
}
```

## Orchestrator Design

The discussion orchestrator (ADK LoopAgent) acts as A2A client:
1. Creates a task for each Clone's turn
2. Sends full conversation history + topic
3. Receives grounded response + citations
4. Posts response + citations to Matrix room
5. Loops for configured number of turns

Turn selection: round-robin by default, or LLM-decided based on
conversation flow (configurable per discussion).
