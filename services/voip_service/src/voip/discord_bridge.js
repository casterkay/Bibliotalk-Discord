import { PassThrough } from "node:stream";

import {
  EndBehaviorType,
  NoSubscriberBehavior,
  StreamType,
  VoiceConnectionStatus,
  createAudioPlayer,
  createAudioResource,
  entersState,
  joinVoiceChannel,
} from "@discordjs/voice";
import prism from "prism-media";
import WebSocket from "ws";

import { AgentsLiveVoiceClient } from "./live_voice_client.js";
import {
  decodePcmS16Le,
  encodeB64,
  pcm24kMonoTo48kStereoS16le,
  pcm48kStereoTo16kMonoS16le,
} from "./pcm.js";

function nowIso() {
  return new Date().toISOString();
}

function toUtf8(data) {
  if (typeof data === "string") return data;
  if (Buffer.isBuffer(data)) return data.toString("utf-8");
  if (data instanceof ArrayBuffer) return Buffer.from(data).toString("utf-8");
  return Buffer.from(data).toString("utf-8");
}

function safeJsonParse(data) {
  try {
    return JSON.parse(toUtf8(data));
  } catch {
    return null;
  }
}

export class DiscordVoiceBridge {
  constructor(config) {
    this.bridgeId = config.bridgeId;
    this.platform = "discord";
    this.guildId = config.guildId;
    this.voiceChannelId = config.voiceChannelId;
    this._guildId = config.guildId;
    this._voiceChannelId = config.voiceChannelId;
    this._agentId = config.agentId;
    this._initiatorUserId = config.initiatorUserId;
    this._textChannelId = config.textChannelId || null;
    this._textThreadId = config.textThreadId || null;
    this._selfMute = Boolean(config.selfMute);
    this._selfDeaf = Boolean(config.selfDeaf);
    this._agentsServiceUrl = config.agentsServiceUrl;
    this._turnId = config.turnId;
    this._onStopped = config.onStopped;

    this._state = "idle";
    this._stopRequested = false;

    this._agents = null;
    this._agentsWs = null;

    this._gatewaySocket = null;
    this._gatewayOutbox = [];
    this._gatewayMethods = null;
    this._gatewayWaiters = [];

    this._voiceConnection = null;
    this._audioPlayer = null;
    this._playbackPcm = null;
    this._playbackEncoder = null;
    this._playbackResource = null;
    this._speakerStreams = new Map();
  }

  isRunning() {
    return this._state === "running" || this._state === "starting";
  }

  attachGatewaySocket(socket) {
    if (this._gatewaySocket && this._gatewaySocket !== socket) {
      try {
        this._gatewaySocket.close(1012, "replaced");
      } catch {
        // ignore
      }
    }
    this._gatewaySocket = socket;
    this._flushGatewayOutbox();
    this._resolveGatewayWaiters();

    socket.on("message", (data) => this._onGatewayMessage(data));
    socket.on("close", () => {
      if (this._gatewaySocket === socket) {
        this._gatewaySocket = null;
      }
    });
  }

  async start() {
    if (this._state !== "idle") return;
    this._state = "starting";

    try {
      this._agents = new AgentsLiveVoiceClient({
        agentsServiceUrl: this._agentsServiceUrl,
        agentId: this._agentId,
        platform: "discord",
        roomId: `${this._guildId}:${this._voiceChannelId}`,
        initiatorPlatformUserId: this._initiatorUserId,
      });
      const { wsUrl } = await this._agents.createSession();

      this._agentsWs = new WebSocket(wsUrl);
      await new Promise((resolve, reject) => {
        this._agentsWs.on("open", () => resolve());
        this._agentsWs.on("error", (err) => reject(err));
      });
      this._agentsWs.on("message", (data) => this._onAgentsMessage(data));
      this._agentsWs.on("close", () => this.stop("agents_ws_closed"));

      await this._waitForGatewaySocket(20000);

      this._voiceConnection = joinVoiceChannel({
        guildId: this._guildId,
        channelId: this._voiceChannelId,
        selfMute: this._selfMute,
        selfDeaf: this._selfDeaf,
        adapterCreator: (methods) => {
          this._gatewayMethods = methods;
          return {
            sendPayload: (payload) => this._sendGatewayVoiceStateUpdate(payload),
            destroy: () => {
              if (this._gatewayMethods === methods) this._gatewayMethods = null;
            },
          };
        },
      });

      this._wireReceiver();
      this._resetPlaybackPipeline();
      this._voiceConnection.subscribe(this._audioPlayer);
      await entersState(this._voiceConnection, VoiceConnectionStatus.Ready, 30000);
      this._state = "running";
    } catch (err) {
      await this.stop("start_failed");
      throw err;
    }
  }

  async stop(reason) {
    if (this._stopRequested) return;
    this._stopRequested = true;
    const prev = this._state;
    this._state = "stopping";

    this._sendAgentsEnvelope("input.audio.stream_end", {});
    this._requestVoiceStateChange({ channel_id: null, self_mute: false, self_deaf: false });

    for (const streams of this._speakerStreams.values()) {
      streams.opus?.destroy();
      streams.decoder?.destroy();
    }
    this._speakerStreams.clear();

    try {
      this._agentsWs?.close();
    } catch {
      // ignore
    }

    try {
      this._voiceConnection?.destroy();
    } catch {
      // ignore
    }
    this._voiceConnection = null;

    try {
      this._audioPlayer?.stop(true);
    } catch {
      // ignore
    }
    this._audioPlayer = null;

    try {
      this._playbackPcm?.destroy();
    } catch {
      // ignore
    }
    this._playbackPcm = null;
    this._playbackEncoder = null;
    this._playbackResource = null;

    this._state = "stopped";
    this._onStopped?.({ bridgeId: this.bridgeId, previous_state: prev, reason });
  }

  _onGatewayMessage(raw) {
    const msg = safeJsonParse(raw);
    if (!msg || typeof msg !== "object") return;
    const type = String(msg.type || "");
    const payload = msg.payload || {};

    if (type === "gateway.voice_state_update") {
      const event = payload?.d || payload;
      this._gatewayMethods?.onVoiceStateUpdate?.(event);
      return;
    }
    if (type === "gateway.voice_server_update") {
      const event = payload?.d || payload;
      this._gatewayMethods?.onVoiceServerUpdate?.(event);
    }
  }

  _sendGatewayVoiceStateUpdate(payload) {
    const event = payload?.d || {};
    this._requestVoiceStateChange({
      guild_id: String(event.guild_id || this._guildId),
      channel_id: event.channel_id == null ? null : String(event.channel_id),
      self_mute: Boolean(event.self_mute),
      self_deaf: Boolean(event.self_deaf),
    });
    return true;
  }

  _requestVoiceStateChange(payload) {
    this._enqueueGatewayMessage("gateway.request_change_voice_state", {
      guild_id: String(payload.guild_id || this._guildId),
      channel_id: payload.channel_id == null ? null : String(payload.channel_id),
      self_mute: Boolean(payload.self_mute),
      self_deaf: Boolean(payload.self_deaf),
    });
  }

  _enqueueGatewayMessage(type, payload) {
    this._gatewayOutbox.push({ type, payload });
    if (this._gatewayOutbox.length > 256) {
      this._gatewayOutbox.shift();
    }
    this._flushGatewayOutbox();
  }

  _flushGatewayOutbox() {
    if (!this._gatewaySocket || this._gatewaySocket.readyState !== WebSocket.OPEN) return;
    while (this._gatewayOutbox.length > 0) {
      const msg = this._gatewayOutbox.shift();
      this._gatewaySocket.send(JSON.stringify({ type: msg.type, ts: nowIso(), payload: msg.payload }));
    }
  }

  _resolveGatewayWaiters() {
    if (!this._gatewaySocket || this._gatewaySocket.readyState !== WebSocket.OPEN) return;
    const waiters = this._gatewayWaiters;
    this._gatewayWaiters = [];
    for (const waiter of waiters) waiter.resolve();
  }

  async _waitForGatewaySocket(timeoutMs) {
    if (this._gatewaySocket && this._gatewaySocket.readyState === WebSocket.OPEN) return;
    await new Promise((resolve, reject) => {
      const timeout = setTimeout(() => {
        reject(new Error("Discord gateway proxy socket not connected"));
      }, timeoutMs);
      this._gatewayWaiters.push({
        resolve: () => {
          clearTimeout(timeout);
          resolve();
        },
      });
    });
  }

  _wireReceiver() {
    if (!this._voiceConnection) return;
    const receiver = this._voiceConnection.receiver;
    receiver.speaking.on("start", (userId) => this._startSpeakerStream(userId));
    receiver.speaking.on("end", (userId) => this._endSpeakerStream(userId));
  }

  _startSpeakerStream(userId) {
    if (this._stopRequested || this._speakerStreams.has(userId)) return;
    this._resetPlaybackPipeline();
    this._audioPlayer?.stop(true);
    this._audioPlayer?.play(this._playbackResource);

    const opus = this._voiceConnection.receiver.subscribe(userId, {
      end: {
        behavior: EndBehaviorType.AfterSilence,
        duration: 120,
      },
    });
    const decoder = new prism.opus.Decoder({ frameSize: 960, channels: 2, rate: 48000 });
    opus.pipe(decoder);

    decoder.on("data", (chunk) => {
      if (this._stopRequested) return;
      const pcm16k = pcm48kStereoTo16kMonoS16le(chunk);
      this._sendAgentsEnvelope("input.audio.chunk", {
        pcm16k_b64: encodeB64(pcm16k),
        participant: String(userId),
      });
    });
    decoder.on("error", () => this._endSpeakerStream(userId));
    opus.on("error", () => this._endSpeakerStream(userId));
    opus.on("close", () => this._endSpeakerStream(userId));
    opus.on("end", () => this._endSpeakerStream(userId));

    this._speakerStreams.set(userId, { opus, decoder });
  }

  _endSpeakerStream(userId) {
    const existing = this._speakerStreams.get(userId);
    if (!existing) return;
    this._speakerStreams.delete(userId);
    existing.opus?.destroy();
    existing.decoder?.destroy();
  }

  _sendAgentsEnvelope(type, payload) {
    if (!this._agentsWs || this._agentsWs.readyState !== WebSocket.OPEN) return;
    this._agentsWs.send(
      JSON.stringify({
        type,
        ts: nowIso(),
        turn_id: this._turnId,
        payload,
      }),
    );
  }

  _onAgentsMessage(raw) {
    const msg = safeJsonParse(raw);
    if (!msg) return;
    if (msg.turn_id && String(msg.turn_id) !== this._turnId) return;
    const type = String(msg.type || "");
    const payload = msg.payload || {};

    if (type === "output.audio.chunk") {
      const pcmB64 = String(payload.pcm24k_b64 || "");
      if (!pcmB64 || !this._playbackPcm) return;
      const pcm24k = decodePcmS16Le(pcmB64);
      const pcm48kStereo = pcm24kMonoTo48kStereoS16le(pcm24k);
      this._playbackPcm.write(pcm48kStereo);
      return;
    }

    if (type === "output.interrupted") {
      this._resetPlaybackPipeline();
      this._audioPlayer?.stop(true);
      this._audioPlayer?.play(this._playbackResource);
      return;
    }

    if (type === "output.transcription.input") {
      this._enqueueGatewayMessage("discord.transcription.input", {
        bridge_id: this.bridgeId,
        guild_id: this._guildId,
        voice_channel_id: this._voiceChannelId,
        text_channel_id: this._textChannelId,
        text_thread_id: this._textThreadId,
        agent_id: this._agentId,
        text: String(payload.text || ""),
        is_final: Boolean(payload.is_final ?? true),
      });
      return;
    }

    if (type === "output.transcription.output") {
      this._enqueueGatewayMessage("discord.transcription.output", {
        bridge_id: this.bridgeId,
        guild_id: this._guildId,
        voice_channel_id: this._voiceChannelId,
        text_channel_id: this._textChannelId,
        text_thread_id: this._textThreadId,
        agent_id: this._agentId,
        text: String(payload.text || ""),
        is_final: Boolean(payload.is_final ?? true),
      });
      return;
    }
  }

  _resetPlaybackPipeline() {
    try {
      this._playbackPcm?.destroy();
    } catch {
      // ignore
    }
    this._playbackPcm = new PassThrough();
    this._playbackEncoder = new prism.opus.Encoder({
      frameSize: 960,
      channels: 2,
      rate: 48000,
    });
    const opus = this._playbackPcm.pipe(this._playbackEncoder);
    this._playbackResource = createAudioResource(opus, {
      inputType: StreamType.Opus,
    });

    if (!this._audioPlayer) {
      this._audioPlayer = createAudioPlayer({
        behaviors: {
          noSubscriber: NoSubscriberBehavior.Pause,
        },
      });
    }
    this._audioPlayer.play(this._playbackResource);
  }
}
