import type { MatrixRoomMessageEvent } from "./events.js";

export type RoomKind = "archive" | "dialogue" | "unknown";

export type RoomKindResolver = {
  getKind(roomId: string): RoomKind;
};

export type GuardConfig = {
  spiritUserPrefix: string; // e.g. "bt_" (not including leading "@")
  roomKinds?: RoomKindResolver;
};

export function isSpiritUserId(userId: string, prefix: string): boolean {
  return userId.startsWith(`@${prefix}`);
}

export function isEditEvent(event: MatrixRoomMessageEvent): boolean {
  const rel = event.content["m.relates_to"];
  return Boolean(rel && rel.rel_type === "m.replace");
}

export function isEligibleTextMessage(event: MatrixRoomMessageEvent): boolean {
  return event.content.msgtype === "m.text" || event.content.msgtype === "m.notice";
}

export function shouldIgnoreMessage(event: MatrixRoomMessageEvent, config: GuardConfig): boolean {
  if (isSpiritUserId(event.sender, config.spiritUserPrefix)) return true;
  if (!isEligibleTextMessage(event)) return true;
  if (isEditEvent(event)) return true;

  const kind = config.roomKinds?.getKind(event.room_id) ?? "unknown";
  if (kind === "archive") return true;

  return false;
}
