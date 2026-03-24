import WebSocket from "ws";
import {
  AudioFrame,
  AudioSource,
  AudioStream,
  LocalAudioTrack,
  Room,
  RoomEvent,
} from "@livekit/rtc-node";

import { AgentsLiveVoiceClient } from "./live_voice_client.js";
import { decodePcmS16Le, encodeB64, PcmRingBuffer, pcm24kTo48kS16le } from "./pcm.js";
import { httpJson } from "./http_utils.js";

function nowIso() {
  return new Date().toISOString();
}

function audioFrameDataToBuffer(frame) {
  const data = frame?.data;
  if (!data) return Buffer.alloc(0);
  if (Buffer.isBuffer(data)) return data;
  if (data instanceof Int16Array || data instanceof Uint8Array) {
    return Buffer.from(data.buffer, data.byteOffset, data.byteLength);
  }
  return Buffer.from(data);
}

function stripTrailingSlash(url) {
  return url.endsWith("/") ? url.slice(0, -1) : url;
}

function toLivekitWsUrl(url) {
  const u = String(url || "").trim();
  if (!u) throw new Error("Missing LiveKit URL");
  if (u.startsWith("ws://") || u.startsWith("wss://")) return u;
  if (u.startsWith("http://")) return `ws://${u.slice("http://".length)}`;
  if (u.startsWith("https://")) return `wss://${u.slice("https://".length)}`;
  return u;
}

export class MatrixLiveKitBridge {
  constructor(config) {
    this.bridgeId = config.bridgeId;
    this.platform = "matrix";
    this.roomId = config.roomId;
    this._spiritUserId = config.spiritUserId;
    this._agentId = config.agentId;
    this._livekitServiceUrl = stripTrailingSlash(config.livekitServiceUrl);
    this._matrix = config.matrix;
    this._agentsServiceUrl = config.agentsServiceUrl;
    this._onStopped = config.onStopped;
    this._turnId = config.turnId;

    this._stopRequested = false;
    this._state = "idle";

    this._agents = null;
    this._agentsWs = null;

    this._lkRoom = null;
    this._lkAudioSource = null;
    this._lkTrack = null;
    this._lkOutPcm = new PcmRingBuffer({ bytesPerSample: 2 });

    this._remoteAudioTasks = [];
  }

  isRunning() {
    return this._state === "running" || this._state === "starting";
  }

  async start() {
    if (this._state !== "idle") return;
    this._state = "starting";

    try {
      await this._matrix.sendNotice(this.roomId, this._spiritUserId, "Call started");

      this._agents = new AgentsLiveVoiceClient({
        agentsServiceUrl: this._agentsServiceUrl,
        agentId: this._agentId,
        platform: "matrix",
        roomId: this.roomId,
        initiatorPlatformUserId: this._spiritUserId,
      });
      const { wsUrl } = await this._agents.createSession();

      this._agentsWs = new WebSocket(wsUrl);
      await new Promise((resolve, reject) => {
        this._agentsWs.on("open", () => resolve());
        this._agentsWs.on("error", (err) => reject(err));
      });
      this._agentsWs.on("message", (data) => this._onAgentsMessage(data));
      this._agentsWs.on("close", () => this.stop("agents_ws_closed"));

      const openid = await this._matrix.requestOpenIdToken(this._spiritUserId);
      const jwtRes = await httpJson("POST", `${this._livekitServiceUrl}/get_token`, {
        room_id: this.roomId,
        slot_id: "m.call#ROOM",
        openid_token: openid,
        member: {
          id: `bt-voip:${this._agentId}`,
          claimed_user_id: this._spiritUserId,
          claimed_device_id: "bt-voip",
        },
        delayed_event_id: "",
      });
      const livekitUrl = String(jwtRes.url || "");
      const livekitJwt = String(jwtRes.jwt || "");
      if (!livekitUrl || !livekitJwt) {
        throw new Error(
          `lk-jwt-service response missing url/jwt: ${JSON.stringify(jwtRes).slice(0, 2000)}`,
        );
      }

      this._lkRoom = new Room();
      this._lkRoom
        .on(RoomEvent.TrackSubscribed, (track, _pub, participant) => {
          if (track.kind !== "audio") return;
          if (participant.identity === this._lkRoom.localParticipant.identity) return;
          this._startRemoteAudioForward(track, participant.identity).catch((err) => {
            // eslint-disable-next-line no-console
            console.error("remote audio forward failed", { room_id: this.roomId, err });
          });
        })
        .on(RoomEvent.Disconnected, () => this.stop("livekit_disconnected"));

      await this._lkRoom.connect(toLivekitWsUrl(livekitUrl), livekitJwt);

      this._lkAudioSource = new AudioSource(48000, 1);
      this._lkTrack = LocalAudioTrack.createAudioTrack("bt-spirit-mic", this._lkAudioSource);
      await this._lkRoom.localParticipant.publishTrack(this._lkTrack);
      this._flushLivekitAudio();

      this._state = "running";
    } catch (err) {
      try {
        await this._matrix.sendNotice(
          this.roomId,
          this._spiritUserId,
          `Call failed: ${String(err?.message || err)}`,
        );
      } catch {
        // ignore
      }
      await this.stop("start_failed");
      throw err;
    }
  }

  async stop(reason) {
    if (this._stopRequested) return;
    this._stopRequested = true;
    const prev = this._state;
    this._state = "stopping";

    try {
      if (this._agentsWs && this._agentsWs.readyState === WebSocket.OPEN) {
        this._agentsWs.send(
          JSON.stringify({
            type: "input.audio.stream_end",
            ts: nowIso(),
            turn_id: this._turnId,
            payload: {},
          }),
        );
      }
    } catch {
      // ignore
    }

    for (const task of this._remoteAudioTasks) task.abort?.();
    this._remoteAudioTasks = [];

    try {
      this._agentsWs?.close();
    } catch {
      // ignore
    }

    try {
      this._lkTrack?.stop();
    } catch {
      // ignore
    }

    try {
      this._lkRoom?.disconnect();
    } catch {
      // ignore
    }

    try {
      await this._matrix.sendNotice(this.roomId, this._spiritUserId, `Call ended${reason ? ` (${reason})` : ""}`);
    } catch {
      // ignore
    }

    this._state = "stopped";
    this._onStopped?.({ bridgeId: this.bridgeId, previous_state: prev });
  }

  async _startRemoteAudioForward(track, identity) {
    const controller = new AbortController();
    this._remoteAudioTasks.push(controller);

    const stream = new AudioStream(track, 16000, 1);
    for await (const frame of stream) {
      if (controller.signal.aborted || this._stopRequested) break;
      const b64 = encodeB64(audioFrameDataToBuffer(frame));
      this._agentsWs?.send(
        JSON.stringify({
          type: "input.audio.chunk",
          ts: nowIso(),
          turn_id: this._turnId,
          payload: { pcm16k_b64: b64, participant: identity },
        }),
      );
    }
  }

  _onAgentsMessage(data) {
    let msg;
    try {
      msg = JSON.parse(data.toString("utf-8"));
    } catch {
      return;
    }
    if (msg.turn_id && String(msg.turn_id) !== this._turnId) return;
    const type = String(msg.type || "");
    const payload = msg.payload || {};

    if (type === "output.audio.chunk") {
      const pcmB64 = String(payload.pcm24k_b64 || "");
      if (!pcmB64) return;
      const pcm24k = decodePcmS16Le(pcmB64);
      const pcm48k = pcm24kTo48kS16le(pcm24k);
      this._lkOutPcm.push(pcm48k);
      this._flushLivekitAudio();
      return;
    }

    if (type === "output.interrupted") {
      this._lkOutPcm = new PcmRingBuffer({ bytesPerSample: 2 });
      return;
    }

    if (type === "output.transcription.input") {
      const text = String(payload.text || "").trim();
      if (text) void this._matrix.sendNotice(this.roomId, this._spiritUserId, `User: ${text}`);
      return;
    }

    if (type === "output.transcription.output") {
      const text = String(payload.text || "").trim();
      if (text) void this._matrix.sendNotice(this.roomId, this._spiritUserId, `Spirit: ${text}`);
    }
  }

  _flushLivekitAudio() {
    if (!this._lkAudioSource) return;
    const frameSamples = 480;

    while (this._lkOutPcm.samplesAvailable() >= frameSamples) {
      const pcmBytes = this._lkOutPcm.popSamples(frameSamples);
      const pcm = new Int16Array(
        pcmBytes.buffer,
        pcmBytes.byteOffset,
        Math.floor(pcmBytes.byteLength / 2),
      );
      const frame = new AudioFrame(pcm, 48000, 1, frameSamples);
      this._lkAudioSource.captureFrame(frame);
    }
  }
}
