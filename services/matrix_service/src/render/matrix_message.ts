export type CitationV1 = {
  segment_id: string;
  emos_message_id: string;
  source_title: string;
  source_url: string;
  quote: string;
  content_platform: string;
  timestamp?: string | null;
};

export type CitedMessage = {
  msgtype: "m.text";
  body: string;
  format: "org.matrix.custom.html";
  formatted_body: string;
  "com.bibliotalk.citations": { version: "1"; items: CitationV1[] };
};

function escapeHtml(input: string): string {
  return input
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#39;");
}

export function renderCitedMessage(text: string, citations: CitationV1[]): CitedMessage {
  const items = citations ?? [];
  const lines: string[] = [text.trim()];

  if (items.length > 0) {
    lines.push("");
    lines.push("Sources:");
    for (const [idx, c] of items.entries()) {
      lines.push(`[${idx + 1}] ${c.source_title} — ${c.source_url}`);
    }
  }

  const body = lines.join("\n").trim();
  const formatted = escapeHtml(body).replaceAll("\n", "<br/>");

  return {
    msgtype: "m.text",
    body,
    format: "org.matrix.custom.html",
    formatted_body: formatted,
    "com.bibliotalk.citations": { version: "1", items },
  };
}
