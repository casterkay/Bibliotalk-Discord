export function encodeB64(buf) {
  return Buffer.from(buf).toString("base64");
}

export function decodePcmS16Le(b64) {
  return Buffer.from(b64, "base64");
}

export function pcm24kTo48kS16le(pcm24kBuf) {
  return pcm24kMonoTo48kS16le(pcm24kBuf);
}

export function pcm24kMonoTo48kS16le(pcm24kBuf) {
  const inSamples = pcm24kBuf.length / 2;
  const out = Buffer.allocUnsafe(inSamples * 2 * 2);
  for (let i = 0; i < inSamples; i++) {
    const lo = pcm24kBuf[i * 2];
    const hi = pcm24kBuf[i * 2 + 1];
    const j = i * 4;
    out[j] = lo;
    out[j + 1] = hi;
    out[j + 2] = lo;
    out[j + 3] = hi;
  }
  return out;
}

export function pcm24kMonoTo48kStereoS16le(pcm24kBuf) {
  const inSamples = Math.floor(pcm24kBuf.length / 2);
  const out = Buffer.allocUnsafe(inSamples * 2 * 2 * 2);
  for (let i = 0; i < inSamples; i++) {
    const sample = pcm24kBuf.readInt16LE(i * 2);
    const j = i * 8;
    out.writeInt16LE(sample, j);
    out.writeInt16LE(sample, j + 2);
    out.writeInt16LE(sample, j + 4);
    out.writeInt16LE(sample, j + 6);
  }
  return out;
}

function clampInt16(value) {
  if (value > 32767) return 32767;
  if (value < -32768) return -32768;
  return value;
}

export function pcm48kStereoTo16kMonoS16le(pcm48kStereo) {
  const frameBytes = 4;
  const totalFrames = Math.floor(pcm48kStereo.length / frameBytes);
  const outFrames = Math.floor(totalFrames / 3);
  const out = Buffer.allocUnsafe(outFrames * 2);

  for (let outIndex = 0; outIndex < outFrames; outIndex++) {
    const inFrame = outIndex * 3;
    const inByte = inFrame * frameBytes;
    const left = pcm48kStereo.readInt16LE(inByte);
    const right = pcm48kStereo.readInt16LE(inByte + 2);
    const mono = clampInt16(Math.trunc((left + right) / 2));
    out.writeInt16LE(mono, outIndex * 2);
  }
  return out;
}

export class PcmRingBuffer {
  constructor({ bytesPerSample }) {
    this._bytesPerSample = bytesPerSample;
    this._buf = Buffer.alloc(0);
  }

  push(buf) {
    if (!buf || buf.length === 0) return;
    this._buf = this._buf.length === 0 ? Buffer.from(buf) : Buffer.concat([this._buf, buf]);
  }

  samplesAvailable() {
    return Math.floor(this._buf.length / this._bytesPerSample);
  }

  popSamples(numSamples) {
    const bytes = numSamples * this._bytesPerSample;
    if (this._buf.length < bytes) {
      throw new Error("insufficient samples");
    }
    const out = this._buf.subarray(0, bytes);
    this._buf = this._buf.subarray(bytes);
    return out;
  }
}
