# ingestion_service

Standalone Python package + CLI for ingesting curated, operator-provided content into EverMemOS.

Primary entry point:

- `python -m ingestion_service --help`

This package focuses on deterministic chunking, stable IDs, safe re-runs (idempotency), and per-source JSON reporting.

## CLI

Web and document ingestion use optional extras:

- Web extraction + blog discovery: `pip install 'ingestion_service[web]'`
- Document conversion (pdf/docx/epub/html/…): `pip install 'ingestion_service[docs]'`

Commands:

- `python -m ingestion_service ingest web --help`
- `python -m ingestion_service ingest doc-url --help`
- `python -m ingestion_service crawl blog --help`
- `python -m ingestion_service crawl rss --help`

## FastAPI Server

Run the ingestion API server:

- `uv run uvicorn ingestion_service.server:app --host 0.0.0.0 --port 8080`

Endpoints:

- `GET /health`
- `POST /ingest/text`
- `POST /ingest/file`
- `POST /ingest/manifest`

`POST /ingest/manifest` request body:

```json
{
  "manifest": {
    "version": "2",
    "sources": [
      {
        "user_id": "confucius",
        "platform": "gutenberg",
        "external_id": "3330",
        "title": "The Analects",
        "gutenberg_id": "3330"
      }
    ]
  }
}
```

## Figure JSON Ingestion Script

Script:

- `scripts/ingest_from_figures_json.py`

Example:

- `uv run python scripts/ingest_from_figures_json.py --input /absolute/path/to/figures.json`

What it does:

- Reads figure JSON (`{ "<Figure Name>": { "avatar": "...", "bio": "...", "sources": [...] } }`)
- Converts supported source URLs into ingest manifest items
- Runs manifest ingestion
- Writes ingestion report JSON
- Appends per-user segment cache into `.ingestion_service/segment_cache/<user_id>.jsonl`

Playlist expansion uses `yt-dlp`:

- `yt-dlp --flat-playlist --print "https://www.youtube.com/watch?v=%(id)s" "https://www.youtube.com/playlist?list=<PLAYLIST_ID>"`
