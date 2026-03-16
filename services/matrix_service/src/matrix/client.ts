import { randomUUID } from "node:crypto";

export type MatrixClientConfig = {
  homeserverUrl: string;
  asToken: string;
};

type Json = Record<string, unknown>;

function withTrailingSlash(url: string): string {
  return url.endsWith("/") ? url : `${url}/`;
}

function buildUrl(baseUrl: string, path: string, query: Record<string, string | undefined>): string {
  const url = new URL(path.replace(/^[\\/]+/, ""), withTrailingSlash(baseUrl));
  for (const [k, v] of Object.entries(query)) {
    if (v) url.searchParams.set(k, v);
  }
  return url.toString();
}

async function requestJson<T>(method: string, url: string, body: Json | null): Promise<T> {
  const res = await fetch(url, {
    method,
    headers: { "content-type": "application/json" },
    body: body ? JSON.stringify(body) : undefined,
  });
  if (!res.ok) {
    const text = await res.text();
    throw new Error(`Matrix request failed (${res.status}) ${method} ${url}: ${text}`);
  }
  return (await res.json()) as T;
}

export class MatrixClient {
  private homeserverUrl: string;
  private asToken: string;

  constructor(config: MatrixClientConfig) {
    this.homeserverUrl = config.homeserverUrl;
    this.asToken = config.asToken;
  }

  async joinRoomAsUser(roomId: string, userId: string): Promise<void> {
    const url = buildUrl(this.homeserverUrl, `/_matrix/client/v3/join/${encodeURIComponent(roomId)}`, {
      access_token: this.asToken,
      user_id: userId,
    });
    await requestJson("POST", url, {});
  }

  async sendMessageAsUser(roomId: string, userId: string, content: Json): Promise<string> {
    const txnId = randomUUID();
    const url = buildUrl(
      this.homeserverUrl,
      `/_matrix/client/v3/rooms/${encodeURIComponent(roomId)}/send/m.room.message/${encodeURIComponent(txnId)}`,
      { access_token: this.asToken, user_id: userId },
    );
    const res = await requestJson<{ event_id: string }>("PUT", url, content);
    return res.event_id;
  }

  async editMessageAsUser(roomId: string, userId: string, targetEventId: string, newContent: Json): Promise<string> {
    const content: Json = {
      ...newContent,
      "m.new_content": newContent,
      "m.relates_to": { rel_type: "m.replace", event_id: targetEventId },
    };
    return await this.sendMessageAsUser(roomId, userId, content);
  }
}
