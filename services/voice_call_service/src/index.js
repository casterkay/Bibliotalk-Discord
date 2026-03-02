import { joinMatrixRtc } from "./matrixrtc.js";
import { createAudioBridge } from "./audio_bridge.js";

async function main() {
  const bridge = createAudioBridge();
  await joinMatrixRtc({ bridge });
}

main().catch((err) => {
  console.error("sidecar failed", err);
  process.exit(1);
});
