# evermemos_ingest

Standalone Python package + CLI for ingesting curated, operator-provided content into EverMemOS.

Primary entry point:

- `python -m evermemos_ingest --help`

This package focuses on deterministic chunking, stable IDs, safe re-runs (idempotency), and per-source JSON reporting.

