# ingestion_service

Standalone Python package + CLI for ingesting curated, operator-provided content into EverMemOS.

Primary entry point:

- `python -m ingestion_service --help`

This package focuses on deterministic chunking, stable IDs, safe re-runs (idempotency), and per-source JSON reporting.
