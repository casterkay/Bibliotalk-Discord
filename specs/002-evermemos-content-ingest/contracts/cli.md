# Contract: CLI Commands (evermemos_ingest)

**Feature**: `/Users/tcai/Projects/Bibliotalk/specs/002-evermemos-content-ingest/spec.md`  
**Created**: 2026-03-01

This contract defines the CLI surface area. The CLI is the primary operator interface and must remain stable.

## Entry Points

- Module: `python -m evermemos_ingest ...`
- (Optional packaging) Console script: `evermemos-ingest ...`

## Global Options

- `--emos-base-url` (string, optional if `EMOS_BASE_URL` is set)
- `--emos-api-key` (string, optional if `EMOS_API_KEY` is set; must not be echoed in logs)
- `--index-path` (string, optional if `INGEST_INDEX_PATH` is set)
- `--report-path` (string, optional): where to write the JSON report for the run
- `--log-level` (string, optional): `debug|info|warning|error`

## Commands

### 1) `ingest text`

Ingest operator-provided text as a single source.

Required:
- `--user-id`
- `--platform`
- `--external-id`
- `--title`
- `--text`

Optional:
- `--canonical-url`
- `--author`
- `--published-at`

### 2) `ingest file`

Ingest a local file as a single source.

Required:
- `--user-id`
- `--platform`
- `--external-id`
- `--title`
- `--path` (absolute path)

Optional:
- `--canonical-url`, `--author`, `--published-at`

### 3) `ingest manifest`

Batch ingest one or more sources described by a manifest file.

Required:
- `--path` (absolute path to YAML/JSON manifest)

## Exit Codes

- `0`: all sources ingested successfully (or skipped as unchanged)
- `1`: at least one source failed
- `2`: invalid CLI usage or invalid manifest

## Output Guarantees

- The CLI MUST write a JSON report (see `report-format.md`) when `--report-path` is provided.
- The CLI MUST never print secrets (API key, auth header) even at debug log level.

