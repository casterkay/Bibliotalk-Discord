from __future__ import annotations

import asyncio
import logging
from dataclasses import dataclass
from pathlib import Path
from typing import Awaitable, Optional, TypeVar

import typer
from bt_common.evermemos_client import EverMemOSClient
from rich.console import Console

from .adapters.local_text import load_text_source
from .adapters.url_tools import url_external_id
from .domain.errors import ConfigError, IngestError, InvalidInputError
from .domain.models import PlainTextContent, Source, SourceContent
from .pipeline.index import IngestionIndex
from .pipeline.ingest import ingest_manifest as ingest_manifest_pipeline
from .pipeline.ingest import ingest_sources
from .pipeline.manifest import load_manifest
from .runtime.config import load_runtime_config
from .runtime.reporting import redact_text, write_report

app = typer.Typer(add_completion=False)
ingest_app = typer.Typer(add_completion=False)
crawl_app = typer.Typer(add_completion=False)
app.add_typer(ingest_app, name="ingest")
app.add_typer(crawl_app, name="crawl")


@dataclass
class CLIContext:
    emos_base_url: str | None
    emos_api_key: str | None
    index_path: str | None
    report_path: str | None
    log_level: str


@app.callback()
def _global(
    ctx: typer.Context,
    emos_base_url: Optional[str] = typer.Option(None, "--emos-base-url"),
    emos_api_key: Optional[str] = typer.Option(None, "--emos-api-key"),
    index_path: Optional[str] = typer.Option(None, "--index-path"),
    report_path: Optional[str] = typer.Option(None, "--report-path"),
    log_level: str = typer.Option("info", "--log-level"),
) -> None:
    ctx.obj = CLIContext(
        emos_base_url=emos_base_url,
        emos_api_key=emos_api_key,
        index_path=index_path,
        report_path=report_path,
        log_level=log_level.lower(),
    )


def _configure_logging(level: str) -> None:
    lvl = getattr(logging, level.upper(), logging.INFO)
    logging.basicConfig(level=lvl, format="%(levelname)s %(message)s")


def _run(coro):
    return asyncio.run(coro)


T = TypeVar("T")


async def _run_with_client_close(
    client: EverMemOSClient,
    operation: Awaitable[T],
) -> T:
    try:
        return await operation
    finally:
        await client.aclose()


def _report_path(cli: CLIContext, *, run_id: str) -> Path:
    if cli.report_path:
        return Path(cli.report_path)
    return (Path.cwd() / ".ingestion_service" / "reports" / f"{run_id}.json").resolve()


def _write_manifest_yaml(*, path: Path, payload: dict) -> None:
    try:
        import yaml  # type: ignore
    except ModuleNotFoundError as exc:  # pragma: no cover
        raise InvalidInputError(
            "PyYAML is required to write YAML manifests. Install with `pip install PyYAML`."
        ) from exc

    path.parent.mkdir(parents=True, exist_ok=True)
    rendered = yaml.safe_dump(payload, sort_keys=False, allow_unicode=True)
    path.write_text(rendered, encoding="utf-8")


@ingest_app.command("text")
def ingest_text(
    ctx: typer.Context,
    user_id: str = typer.Option(..., "--user-id"),
    platform: str = typer.Option(..., "--platform"),
    external_id: str = typer.Option(..., "--external-id"),
    title: str = typer.Option(..., "--title"),
    text: str = typer.Option(..., "--text"),
    source_url: Optional[str] = typer.Option(None, "--canonical-url"),
    author: Optional[str] = typer.Option(None, "--author"),
    published_at: Optional[str] = typer.Option(None, "--published-at"),
) -> None:
    cli: CLIContext = ctx.obj
    _configure_logging(cli.log_level)
    console = Console()

    try:
        cfg = load_runtime_config(
            emos_base_url=cli.emos_base_url,
            emos_api_key=cli.emos_api_key,
            index_path=cli.index_path,
        )
        index = IngestionIndex(cfg.index_path)
        client = EverMemOSClient(
            cfg.emos_base_url,
            api_key=cfg.emos_api_key,
            timeout=cfg.emos_timeout_s,
            retries=cfg.emos_retries,
        )
        source_content = load_text_source(
            user_id=user_id,
            platform=platform,
            external_id=external_id,
            title=title,
            text=text,
            source_url=source_url,
            author=author,
            published_at=published_at,
        )
        report = _run(
            _run_with_client_close(
                client,
                ingest_sources(
                    sources=[source_content],
                    index=index,
                    client=client,
                    redact_secrets=[cfg.emos_api_key or ""],
                ),
            )
        )
    except (ConfigError, InvalidInputError) as exc:
        raise typer.Exit(code=2) from exc
    except IngestError as exc:
        console.print(
            f"[red]Error:[/red] {redact_text(str(exc), secrets=[cli.emos_api_key or ''])}"
        )
        raise typer.Exit(code=1) from exc

    write_report(
        report,
        path=_report_path(cli, run_id=report.run_id),
        secrets=[cfg.emos_api_key or ""],
    )

    src = report.sources[0]
    logging.getLogger("ingestion_service").info(
        "run_id=%s status=%s group_id=%s", report.run_id, report.status, src.group_id
    )
    console.print(
        f"run_id={report.run_id} group_id={src.group_id} status={src.status} ingested={src.segments_ingested} skipped={src.segments_skipped_unchanged} failed={src.segments_failed}"
    )
    raise typer.Exit(code=0 if report.status == "done" else 1)


@ingest_app.command("file")
def ingest_file(
    ctx: typer.Context,
    user_id: str = typer.Option(..., "--user-id"),
    platform: str = typer.Option(..., "--platform"),
    external_id: str = typer.Option(..., "--external-id"),
    title: str = typer.Option(..., "--title"),
    path: Path = typer.Option(..., "--path"),
    source_url: Optional[str] = typer.Option(None, "--canonical-url"),
    author: Optional[str] = typer.Option(None, "--author"),
    published_at: Optional[str] = typer.Option(None, "--published-at"),
) -> None:
    cli: CLIContext = ctx.obj
    _configure_logging(cli.log_level)
    console = Console()

    try:
        cfg = load_runtime_config(
            emos_base_url=cli.emos_base_url,
            emos_api_key=cli.emos_api_key,
            index_path=cli.index_path,
        )
        index = IngestionIndex(cfg.index_path)
        client = EverMemOSClient(
            cfg.emos_base_url,
            api_key=cfg.emos_api_key,
            timeout=cfg.emos_timeout_s,
            retries=cfg.emos_retries,
        )
        from .adapters.document import load_document_file_source

        src = Source(
            user_id=user_id,
            platform=platform,
            external_id=external_id,
            title=title,
            source_url=source_url,
            author=author,
            published_at=published_at,
        )
        source_content = _run(load_document_file_source(source=src, path=path))
        report = _run(
            _run_with_client_close(
                client,
                ingest_sources(
                    sources=[source_content],
                    index=index,
                    client=client,
                    redact_secrets=[cfg.emos_api_key or ""],
                ),
            )
        )
    except (ConfigError, InvalidInputError) as exc:
        raise typer.Exit(code=2) from exc
    except IngestError as exc:
        console.print(
            f"[red]Error:[/red] {redact_text(str(exc), secrets=[cli.emos_api_key or ''])}"
        )
        raise typer.Exit(code=1) from exc

    write_report(
        report,
        path=_report_path(cli, run_id=report.run_id),
        secrets=[cfg.emos_api_key or ""],
    )

    src = report.sources[0]
    logging.getLogger("ingestion_service").info(
        "run_id=%s status=%s group_id=%s", report.run_id, report.status, src.group_id
    )
    console.print(
        f"run_id={report.run_id} group_id={src.group_id} status={src.status} ingested={src.segments_ingested} skipped={src.segments_skipped_unchanged} failed={src.segments_failed}"
    )
    raise typer.Exit(code=0 if report.status == "done" else 1)


@ingest_app.command("web")
def ingest_web(
    ctx: typer.Context,
    user_id: str = typer.Option(..., "--user-id"),
    platform: str = typer.Option("web", "--platform"),
    url: str = typer.Option(..., "--url"),
    external_id: Optional[str] = typer.Option(None, "--external-id"),
    title: Optional[str] = typer.Option(None, "--title"),
    author: Optional[str] = typer.Option(None, "--author"),
    min_words: int = typer.Option(80, "--min-words"),
) -> None:
    cli: CLIContext = ctx.obj
    _configure_logging(cli.log_level)
    console = Console()

    try:
        cfg = load_runtime_config(
            emos_base_url=cli.emos_base_url,
            emos_api_key=cli.emos_api_key,
            index_path=cli.index_path,
        )
        index = IngestionIndex(cfg.index_path)
        client = EverMemOSClient(
            cfg.emos_base_url,
            api_key=cfg.emos_api_key,
            timeout=cfg.emos_timeout_s,
            retries=cfg.emos_retries,
        )

        from .adapters.web_page import extract_web_page_markdown

        extracted = _run(extract_web_page_markdown(url, min_words=min_words))
        resolved_external_id = external_id or url_external_id(extracted.canonical_url)
        resolved_title = extracted.title or title or extracted.canonical_url
        src = Source(
            user_id=user_id,
            platform=platform,
            external_id=resolved_external_id,
            title=resolved_title,
            source_url=extracted.canonical_url,
            author=author,
            published_at=extracted.published_at,
            raw_meta=extracted.raw_meta,
        )
        sc = SourceContent(source=src, content=PlainTextContent(text=extracted.markdown))
        report = _run(
            _run_with_client_close(
                client,
                ingest_sources(
                    sources=[sc],
                    index=index,
                    client=client,
                    redact_secrets=[cfg.emos_api_key or ""],
                ),
            )
        )
    except (ConfigError, InvalidInputError) as exc:
        console.print(f"[red]Invalid input:[/red] {exc}")
        raise typer.Exit(code=2) from exc
    except IngestError as exc:
        console.print(
            f"[red]Error:[/red] {redact_text(str(exc), secrets=[cli.emos_api_key or ''])}"
        )
        raise typer.Exit(code=1) from exc

    write_report(
        report,
        path=_report_path(cli, run_id=report.run_id),
        secrets=[cfg.emos_api_key or ""],
    )
    src_result = report.sources[0]
    console.print(
        f"run_id={report.run_id} group_id={src_result.group_id} status={src_result.status} "
        f"ingested={src_result.segments_ingested} skipped={src_result.segments_skipped_unchanged} failed={src_result.segments_failed}"
    )
    raise typer.Exit(code=0 if report.status == "done" else 1)


@ingest_app.command("doc-url")
def ingest_doc_url(
    ctx: typer.Context,
    user_id: str = typer.Option(..., "--user-id"),
    platform: str = typer.Option("local", "--platform"),
    url: str = typer.Option(..., "--url"),
    external_id: Optional[str] = typer.Option(None, "--external-id"),
    title: Optional[str] = typer.Option(None, "--title"),
    source_url: Optional[str] = typer.Option(None, "--canonical-url"),
    author: Optional[str] = typer.Option(None, "--author"),
    published_at: Optional[str] = typer.Option(None, "--published-at"),
) -> None:
    cli: CLIContext = ctx.obj
    _configure_logging(cli.log_level)
    console = Console()

    try:
        cfg = load_runtime_config(
            emos_base_url=cli.emos_base_url,
            emos_api_key=cli.emos_api_key,
            index_path=cli.index_path,
        )
        index = IngestionIndex(cfg.index_path)
        client = EverMemOSClient(
            cfg.emos_base_url,
            api_key=cfg.emos_api_key,
            timeout=cfg.emos_timeout_s,
            retries=cfg.emos_retries,
        )

        from .adapters.document import load_document_url_source

        resolved_external_id = external_id or url_external_id(url)
        src = Source(
            user_id=user_id,
            platform=platform,
            external_id=resolved_external_id,
            title=title or url,
            source_url=source_url or url,
            author=author,
            published_at=published_at,
        )
        sc = _run(load_document_url_source(source=src, url=url))
        report = _run(
            _run_with_client_close(
                client,
                ingest_sources(
                    sources=[sc],
                    index=index,
                    client=client,
                    redact_secrets=[cfg.emos_api_key or ""],
                ),
            )
        )
    except (ConfigError, InvalidInputError) as exc:
        console.print(f"[red]Invalid input:[/red] {exc}")
        raise typer.Exit(code=2) from exc
    except IngestError as exc:
        console.print(
            f"[red]Error:[/red] {redact_text(str(exc), secrets=[cli.emos_api_key or ''])}"
        )
        raise typer.Exit(code=1) from exc

    write_report(
        report,
        path=_report_path(cli, run_id=report.run_id),
        secrets=[cfg.emos_api_key or ""],
    )
    src_result = report.sources[0]
    console.print(
        f"run_id={report.run_id} group_id={src_result.group_id} status={src_result.status} "
        f"ingested={src_result.segments_ingested} skipped={src_result.segments_skipped_unchanged} failed={src_result.segments_failed}"
    )
    raise typer.Exit(code=0 if report.status == "done" else 1)


@crawl_app.command("rss")
def crawl_rss(
    rss_url: str = typer.Option(..., "--rss-url"),
    user_id: str = typer.Option(..., "--user-id"),
    platform: str = typer.Option("web", "--platform"),
    max_items: int = typer.Option(50, "--max-items"),
    out_path: Path = typer.Option(..., "--out-path"),
) -> None:
    _configure_logging("info")
    console = Console()

    if not out_path.is_absolute():
        out_path = out_path.expanduser().resolve()

    from .adapters.rss_feed import parse_feed

    entries = _run(parse_feed(rss_url, max_items=max_items))
    sources = [
        {
            "title": e.title or e.url,
            "web_url": e.url,
        }
        for e in entries
    ]
    manifest = {
        "version": "2",
        "run_name": f"rss:{rss_url}",
        "defaults": {"user_id": user_id, "platform": platform},
        "sources": sources,
    }
    _write_manifest_yaml(path=out_path, payload=manifest)
    console.print(f"Wrote manifest: {out_path} (sources={len(sources)})")


@crawl_app.command("blog")
def crawl_blog(
    seed_url: str = typer.Option(..., "--seed-url"),
    user_id: str = typer.Option(..., "--user-id"),
    platform: str = typer.Option("web", "--platform"),
    max_items: int = typer.Option(50, "--max-items"),
    max_pages: int = typer.Option(200, "--max-pages"),
    out_path: Path = typer.Option(..., "--out-path"),
) -> None:
    _configure_logging("info")
    console = Console()

    if not out_path.is_absolute():
        out_path = out_path.expanduser().resolve()

    from .adapters.blog_crawl import CrawlConfig, discover_blog_urls

    urls = _run(
        discover_blog_urls(
            seed_url,
            cfg=CrawlConfig(max_items=max_items, max_pages=max_pages),
        )
    )
    sources = [{"title": url, "web_url": url} for url in urls]
    manifest = {
        "version": "2",
        "run_name": f"blog:{seed_url}",
        "defaults": {"user_id": user_id, "platform": platform},
        "sources": sources,
    }
    _write_manifest_yaml(path=out_path, payload=manifest)
    console.print(f"Wrote manifest: {out_path} (sources={len(sources)})")


@ingest_app.command("manifest")
def ingest_manifest_cmd(
    ctx: typer.Context,
    path: Path = typer.Option(..., "--path"),
) -> None:
    cli: CLIContext = ctx.obj
    _configure_logging(cli.log_level)
    console = Console()

    try:
        if not path.is_absolute():
            raise InvalidInputError("--path must be absolute")
        manifest = load_manifest(path)
    except InvalidInputError as exc:
        console.print(f"[red]Invalid manifest:[/red] {exc}")
        raise typer.Exit(code=2) from exc

    try:
        cfg = load_runtime_config(
            emos_base_url=cli.emos_base_url,
            emos_api_key=cli.emos_api_key,
            index_path=cli.index_path,
        )
        index = IngestionIndex(cfg.index_path)
        client = EverMemOSClient(
            cfg.emos_base_url,
            api_key=cfg.emos_api_key,
            timeout=cfg.emos_timeout_s,
            retries=cfg.emos_retries,
        )
        report = _run(
            _run_with_client_close(
                client,
                ingest_manifest_pipeline(
                    manifest=manifest,
                    index=index,
                    client=client,
                    redact_secrets=[cfg.emos_api_key or ""],
                ),
            )
        )
    except (ConfigError, InvalidInputError) as exc:
        console.print(f"[red]Invalid input:[/red] {exc}")
        raise typer.Exit(code=2) from exc
    except IngestError as exc:
        console.print(
            f"[red]Error:[/red] {redact_text(str(exc), secrets=[cli.emos_api_key or ''])}"
        )
        raise typer.Exit(code=1) from exc

    write_report(
        report,
        path=_report_path(cli, run_id=report.run_id),
        secrets=[cfg.emos_api_key or ""],
    )

    logging.getLogger("ingestion_service").info(
        "run_id=%s status=%s sources_total=%s sources_failed=%s",
        report.run_id,
        report.status,
        report.summary.sources_total,
        report.summary.sources_failed,
    )
    console.print(
        f"run_id={report.run_id} status={report.status} sources_total={report.summary.sources_total} "
        f"succeeded={report.summary.sources_succeeded} failed={report.summary.sources_failed}"
    )
    raise typer.Exit(code=0 if report.status == "done" else 1)


if __name__ == "__main__":
    app()
