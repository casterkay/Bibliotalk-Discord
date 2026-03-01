# Contract: Voice Backend Interface

**Service**: bt_agent voice session manager
**Pattern**: Abstract base class with pluggable implementations

## VoiceBackend ABC

```
start_session(system_prompt, tools) → None
send_audio_chunk(pcm_16khz_bytes) → None
receive() → AsyncIterator[VoiceEvent]
end_session() → None
```

## VoiceEvent Types

| Type       | Fields                     | Description                      |
| ---------- | -------------------------- | -------------------------------- |
| AudioChunk | pcm_24khz: bytes           | Clone speech audio               |
| ToolCall   | tool_name: str, args: dict | Model requests a tool invocation |
| Transcript | text: str, role: str       | Transcription of speech          |
| EndOfTurn  | (none)                     | Model finished speaking          |

## Audio Format

| Direction | Format | Sample Rate | Bit Depth | Channels |
| --------- | ------ | ----------- | --------- | -------- |
| Input     | PCM    | 16 kHz      | 16-bit    | Mono     |
| Output    | PCM    | 24 kHz      | 16-bit    | Mono     |

## Tool-Use Mid-Conversation

Nova Sonic supports tool-use during voice sessions:
1. Model pauses audio output
2. Emits `ToolCall` event (tool name + arguments)
3. Caller executes tool, sends result back via tool result event
4. Model resumes generating audio with tool result context

This enables `memory_search` and `emit_citations` to work within
voice conversations, maintaining citation grounding in voice mode.

## Implementations

| Backend           | Transport             | Region    |
| ----------------- | --------------------- | --------- |
| NovaSonicBackend  | Bedrock bidirectional | us-east-1 |
| GeminiLiveBackend | Gemini Live WebSocket | any       |
