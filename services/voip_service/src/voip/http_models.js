function isRecord(value) {
  return typeof value === "object" && value !== null && !Array.isArray(value);
}

function mustString(obj, key) {
  const value = obj[key];
  if (typeof value !== "string" || !value.trim()) {
    throw new Error(`Invalid request: missing ${key}`);
  }
  return value.trim();
}

function optionalString(obj, key) {
  const value = obj[key];
  if (typeof value !== "string") return null;
  const trimmed = value.trim();
  return trimmed ? trimmed : null;
}

function optionalBoolean(obj, key, fallback = null) {
  const value = obj[key];
  if (typeof value === "boolean") return value;
  return fallback;
}

export function parseEnsureRequest(raw) {
  if (!isRecord(raw)) throw new Error("Invalid request: body must be an object");
  const platformRaw = optionalString(raw, "platform");
  const platform = (platformRaw || "matrix").toLowerCase();

  if (platform === "discord") {
    return {
      platform,
      guild_id: mustString(raw, "guild_id"),
      voice_channel_id: mustString(raw, "voice_channel_id"),
      agent_id: mustString(raw, "agent_id"),
      initiator_user_id: mustString(raw, "initiator_user_id"),
      text_channel_id: optionalString(raw, "text_channel_id"),
      text_thread_id: optionalString(raw, "text_thread_id"),
      self_mute: optionalBoolean(raw, "self_mute", false),
      self_deaf: optionalBoolean(raw, "self_deaf", false),
    };
  }

  if (platform !== "matrix") {
    throw new Error(`Invalid request: unsupported platform '${platform}'`);
  }

  return {
    platform,
    room_id: mustString(raw, "room_id"),
    spirit_user_id: mustString(raw, "spirit_user_id"),
    agent_id: mustString(raw, "agent_id"),
    livekit_service_url: optionalString(raw, "livekit_service_url"),
  };
}

export function parseStopRequest(raw) {
  if (raw == null) {
    return { room_id: null, reason: "requested" };
  }
  if (!isRecord(raw)) throw new Error("Invalid request: body must be an object");
  return {
    bridge_id: optionalString(raw, "bridge_id"),
    room_id: optionalString(raw, "room_id"),
    guild_id: optionalString(raw, "guild_id"),
    reason: optionalString(raw, "reason") ?? "requested",
  };
}
