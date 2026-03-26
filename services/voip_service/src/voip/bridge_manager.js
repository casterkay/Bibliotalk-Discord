import { randomUUID } from "node:crypto";

import { DiscordVoiceBridge } from "./discord_bridge.js";
import { MatrixLiveKitBridge } from "./matrix_livekit_bridge.js";
import { MatrixAsClient } from "./matrix_as_client.js";

function bridgeIdForMatrix(roomId) {
  return `matrix:${roomId}`;
}

function bridgeIdForDiscord(guildId, voiceChannelId, agentId) {
  return `discord:${guildId}:${voiceChannelId}:${agentId}`;
}

function asString(value) {
  return String(value || "").trim();
}

export class BridgeManager {
  constructor(config) {
    this._config = config;
    this._matrix = new MatrixAsClient({
      homeserverUrl: config.homeserverUrl,
      asToken: config.matrixAsToken,
    });
    this._bridges = new Map();
  }

  async ensure(params) {
    const platform = asString(params.platform || "matrix") || "matrix";
    if (platform === "matrix") {
      return await this._ensureMatrix(params);
    }
    if (platform === "discord") {
      return await this._ensureDiscord(params);
    }
    throw new Error(`Unsupported platform: ${platform}`);
  }

  async stop(params) {
    const targets = this._selectTargets(params);
    await Promise.all(targets.map(async (bridge) => bridge.stop(params.reason)));
    return {
      stopped: targets.map((bridge) => bridge.bridgeId),
    };
  }

  attachDiscordGatewaySocket(bridgeId, socket) {
    const bridge = this._bridges.get(bridgeId);
    if (!bridge) {
      throw new Error(`Unknown bridge_id: ${bridgeId}`);
    }
    if (bridge.platform !== "discord" || typeof bridge.attachGatewaySocket !== "function") {
      throw new Error(`Bridge ${bridgeId} does not accept Discord gateway sockets`);
    }
    bridge.attachGatewaySocket(socket);
  }

  _selectTargets(params) {
    if (params.bridge_id) {
      const b = this._bridges.get(params.bridge_id);
      return b ? [b] : [];
    }

    if (params.room_id) {
      const b = this._bridges.get(bridgeIdForMatrix(params.room_id));
      return b ? [b] : [];
    }

    if (params.guild_id) {
      return [...this._bridges.values()].filter(
        (bridge) => bridge.platform === "discord" && bridge.guildId === params.guild_id,
      );
    }

    return [...this._bridges.values()];
  }

  async _ensureMatrix(params) {
    const livekitServiceUrl = params.livekit_service_url || this._config.fallbackLivekitServiceUrl || "";
    if (!livekitServiceUrl) {
      throw new Error("Missing livekit_service_url (and VOIP_LIVEKIT_SERVICE_URL fallback is empty)");
    }
    if (!this._config.matrixAsToken) {
      throw new Error("Missing MATRIX_AS_TOKEN");
    }

    const roomId = asString(params.room_id);
    const bridgeId = bridgeIdForMatrix(roomId);
    const existing = this._bridges.get(bridgeId);
    if (existing && existing.isRunning()) {
      return { bridge_id: bridgeId, platform: "matrix", room_id: roomId, state: "running" };
    }

    const bridge = new MatrixLiveKitBridge({
      bridgeId,
      roomId,
      spiritUserId: params.spirit_user_id,
      agentId: params.agent_id,
      livekitServiceUrl,
      turnId: randomUUID(),
      matrix: this._matrix,
      agentsServiceUrl: this._config.agentsServiceUrl,
      onStopped: () => this._bridges.delete(bridgeId),
    });
    this._bridges.set(bridgeId, bridge);
    bridge.start().catch((err) => {
      // eslint-disable-next-line no-console
      console.error("matrix bridge start failed", { bridge_id: bridgeId, room_id: roomId, err });
      this._bridges.delete(bridgeId);
    });

    return { bridge_id: bridgeId, platform: "matrix", room_id: roomId, state: "starting" };
  }

  async _ensureDiscord(params) {
    const guildId = asString(params.guild_id);
    const voiceChannelId = asString(params.voice_channel_id);
    const agentId = asString(params.agent_id);
    const bridgeId = bridgeIdForDiscord(guildId, voiceChannelId, agentId);
    const existing = this._bridges.get(bridgeId);
    if (existing && existing.isRunning()) {
      return {
        bridge_id: bridgeId,
        platform: "discord",
        guild_id: guildId,
        voice_channel_id: voiceChannelId,
        state: "running",
      };
    }

    const bridge = new DiscordVoiceBridge({
      bridgeId,
      guildId,
      voiceChannelId,
      agentId,
      initiatorUserId: params.initiator_user_id,
      botUserId: params.bot_user_id || null,
      textChannelId: params.text_channel_id || null,
      textThreadId: params.text_thread_id || null,
      selfMute: params.self_mute,
      selfDeaf: params.self_deaf,
      turnId: randomUUID(),
      agentsServiceUrl: this._config.agentsServiceUrl,
      onStopped: () => this._bridges.delete(bridgeId),
    });
    this._bridges.set(bridgeId, bridge);
    bridge.start().catch((err) => {
      // eslint-disable-next-line no-console
      console.error("discord bridge start failed", {
        bridge_id: bridgeId,
        guild_id: guildId,
        voice_channel_id: voiceChannelId,
        err,
      });
      this._bridges.delete(bridgeId);
    });

    return {
      bridge_id: bridgeId,
      platform: "discord",
      guild_id: guildId,
      voice_channel_id: voiceChannelId,
      state: "starting",
    };
  }
}
