"""Matrix message formatting helpers."""

from __future__ import annotations

from html import escape

from bt_common.citation import Citation


def format_clone_response(text: str, citations: list[Citation]) -> dict:
    marker_text = text
    html_text = escape(text)

    source_lines = ["", "----------", "Sources:"]
    html_sources = ["<hr><b>Sources:</b><br>"]

    for citation in citations:
        marker = f"[^ {citation.index}]".replace(" ", "")
        if marker not in marker_text:
            marker_text += f" {marker}"
        html_text += f" <sup>[{citation.index}]</sup>"
        source_lines.append(f"[{citation.index}] {citation.source_title} ({citation.platform})")
        html_sources.append(
            f"[{citation.index}] <a href=\"{escape(citation.source_url)}\">{escape(citation.source_title)}</a><br>"
        )

    return {
        "msgtype": "m.text",
        "body": "\n".join([marker_text, *source_lines]),
        "format": "org.matrix.custom.html",
        "formatted_body": f"{html_text}{''.join(html_sources)}",
        "com.bibliotalk.citations": {
            "version": "1",
            "items": [citation.model_dump(mode="json") for citation in citations],
        },
    }
