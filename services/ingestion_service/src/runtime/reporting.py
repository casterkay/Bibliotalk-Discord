from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Iterable

from ..domain.models import IngestReport


_BEARER_RE = re.compile(r"Bearer\\s+[^\\s]+", flags=re.IGNORECASE)


def redact_text(text: str, *, secrets: Iterable[str] = ()) -> str:
    value = text
    for secret in secrets:
        if secret:
            value = value.replace(secret, "<REDACTED>")
    value = _BEARER_RE.sub("Bearer <REDACTED>", value)
    return value


def write_report(report: IngestReport, *, path: Path, secrets: Iterable[str] = ()) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = report.model_dump(mode="json")
    rendered = json.dumps(payload, indent=2, sort_keys=True)
    rendered = redact_text(rendered, secrets=secrets)
    path.write_text(rendered + "\n", encoding="utf-8")
