export async function joinMatrixRtc({ bridge }) {
  // Placeholder join flow. Real MatrixRTC wiring is injected around this call.
  return {
    onAudio: (opusFrame) => bridge.onInboundOpus(opusFrame),
    sendAudio: (opusFrame) => bridge.onOutboundOpus(opusFrame),
  };
}
