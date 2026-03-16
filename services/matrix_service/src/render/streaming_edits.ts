import type { MatrixClient } from "../matrix/client.js";
import type { CitedMessage } from "./matrix_message.js";

export type StreamingEditor = {
  eventId: string;
  pushDelta(delta: string): Promise<void>;
  finalize(finalMessage: CitedMessage): Promise<void>;
  interrupt(reason: "superseded" | "cancelled"): Promise<void>;
};

function escapeHtml(input: string): string {
  return input
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#39;");
}

function toFormattedBody(body: string): string {
  return escapeHtml(body).replaceAll("\n", "<br/>");
}

export async function startStreamingMessage(params: {
  client: MatrixClient;
  roomId: string;
  userId: string;
  initial: CitedMessage;
  placeholderBody?: string;
  minEditIntervalMs?: number;
}): Promise<StreamingEditor> {
  const minEditIntervalMs = params.minEditIntervalMs ?? 350;
  const placeholderBody = params.placeholderBody ?? params.initial.body;
  const initialSend: CitedMessage = {
    ...params.initial,
    body: placeholderBody,
    formatted_body: toFormattedBody(placeholderBody),
  };
  const eventId = await params.client.sendMessageAsUser(params.roomId, params.userId, initialSend);

  let buffer = "";
  let lastEditAt = 0;
  let inflight: Promise<void> | null = null;

  async function editNow(content: CitedMessage): Promise<void> {
    await params.client.editMessageAsUser(params.roomId, params.userId, eventId, content);
  }

  async function scheduleEdit(content: CitedMessage): Promise<void> {
    const now = Date.now();
    const waitMs = Math.max(0, minEditIntervalMs - (now - lastEditAt));
    if (waitMs > 0) await new Promise((r) => setTimeout(r, waitMs));
    lastEditAt = Date.now();
    await editNow(content);
  }

  return {
    eventId,
    async pushDelta(delta: string): Promise<void> {
      buffer += delta;
      const content = { ...params.initial, body: buffer, formatted_body: toFormattedBody(buffer) };
      inflight = scheduleEdit(content).catch(() => undefined);
      await inflight;
    },
    async finalize(finalMessage: CitedMessage): Promise<void> {
      buffer = finalMessage.body;
      if (inflight) await inflight;
      await scheduleEdit(finalMessage);
    },
    async interrupt(reason: "superseded" | "cancelled"): Promise<void> {
      const body = `${buffer}\n\n(${reason})`;
      const content = { ...params.initial, body, formatted_body: toFormattedBody(body) };
      if (inflight) await inflight;
      await scheduleEdit(content);
    },
  };
}
