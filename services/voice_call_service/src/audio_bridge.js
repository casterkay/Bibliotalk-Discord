import WebSocket from "ws";

export function createAudioBridge() {
  const ws = new WebSocket(process.env.BT_AGENT_VOICE_WS || "ws://localhost:8010/ws/voice");

  function onInboundOpus(opusFrame) {
    // Real implementation should decode Opus -> PCM16k and forward.
    if (ws.readyState === WebSocket.OPEN) {
      ws.send(opusFrame);
    }
  }

  function onOutboundOpus(opusFrame) {
    // Real implementation should encode PCM24k -> Opus.
    return opusFrame;
  }

  return { ws, onInboundOpus, onOutboundOpus };
}
