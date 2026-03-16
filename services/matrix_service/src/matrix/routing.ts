import type { MatrixRoomMessageEvent } from "./events.js";
import { isSpiritUserId } from "./guards.js";
import type { MembershipIndex } from "./membership.js";

export type RoutingConfig = {
  spiritUserPrefix: string;
};

function uniq(items: string[]): string[] {
  return [...new Set(items)];
}

export function extractMentionedUserIds(event: MatrixRoomMessageEvent): string[] {
  const userIds = event.content["m.mentions"]?.user_ids ?? [];
  return Array.isArray(userIds) ? userIds.filter((x) => typeof x === "string") : [];
}

export function extractLiteralSpiritMentions(body: string, prefix: string): string[] {
  const escapedPrefix = prefix.replace(/[.*+?^${}()|[\\]\\\\]/g, "\\\\$&");
  const re = new RegExp(`@${escapedPrefix}[^\\s:]+:[^\\s]+`, "g");
  const matches = body.match(re) ?? [];
  return matches;
}

export function routeMessageToSpirits(
  event: MatrixRoomMessageEvent,
  membershipIndex: MembershipIndex,
  config: RoutingConfig,
): string[] {
  const mentioned = extractMentionedUserIds(event).filter((u) => isSpiritUserId(u, config.spiritUserPrefix));
  if (mentioned.length > 0) return uniq(mentioned);

  const literal = extractLiteralSpiritMentions(event.content.body, config.spiritUserPrefix).filter((u) =>
    isSpiritUserId(u, config.spiritUserPrefix),
  );
  if (literal.length > 0) return uniq(literal);

  const roomSpirits = membershipIndex.getRoomSpirits(event.room_id);
  if (roomSpirits.length === 1) return roomSpirits;

  return [];
}
