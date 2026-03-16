import type { MatrixRoomMemberEvent } from "./events.js";
import { isSpiritUserId } from "./guards.js";

export type MembershipConfig = {
  spiritUserPrefix: string;
};

export type MatrixClientLike = {
  joinRoomAsUser(roomId: string, userId: string): Promise<void>;
};

export class MembershipIndex {
  private roomToSpirits = new Map<string, Set<string>>();

  getRoomSpirits(roomId: string): string[] {
    const set = this.roomToSpirits.get(roomId);
    if (!set) return [];
    return [...set];
  }

  setMember(roomId: string, spiritUserId: string, isPresent: boolean): void {
    if (!isPresent) {
      const set = this.roomToSpirits.get(roomId);
      if (!set) return;
      set.delete(spiritUserId);
      if (set.size === 0) this.roomToSpirits.delete(roomId);
      return;
    }

    let set = this.roomToSpirits.get(roomId);
    if (!set) {
      set = new Set<string>();
      this.roomToSpirits.set(roomId, set);
    }
    set.add(spiritUserId);
  }
}

export async function handleMembershipEvent(
  event: MatrixRoomMemberEvent,
  deps: { client: MatrixClientLike; index: MembershipIndex; config: MembershipConfig },
): Promise<void> {
  const spiritUserId = event.state_key;
  if (!isSpiritUserId(spiritUserId, deps.config.spiritUserPrefix)) return;

  const membership = event.content.membership;
  if (membership === "invite") {
    await deps.client.joinRoomAsUser(event.room_id, spiritUserId);
    return;
  }

  if (membership === "join") {
    deps.index.setMember(event.room_id, spiritUserId, true);
    return;
  }

  if (membership === "leave" || membership === "ban") {
    deps.index.setMember(event.room_id, spiritUserId, false);
  }
}
