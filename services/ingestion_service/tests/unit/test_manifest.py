from __future__ import annotations

import json

import pytest

from ingestion_service.domain.errors import InvalidInputError
from ingestion_service.adapters.url_tools import url_external_id
from ingestion_service.pipeline.manifest import load_manifest, resolve_manifest_sources


def test_manifest_requires_exactly_one_mode(tmp_path) -> None:
    raw = {
        "version": "1",
        "sources": [
            {
                "user_id": "u1",
                "platform": "local",
                "external_id": "x",
                "title": "T",
                "text": "a",
                "file_path": "/abs.txt",
            }
        ],
    }
    path = tmp_path / "manifest.json"
    path.write_text(json.dumps(raw), encoding="utf-8")
    with pytest.raises(InvalidInputError):
        load_manifest(path)


def test_manifest_defaults_are_applied(tmp_path) -> None:
    raw = {
        "version": "1",
        "defaults": {"user_id": "u1", "platform": "local"},
        "sources": [{"external_id": "x", "title": "T", "text": "hello"}],
    }
    path = tmp_path / "manifest.json"
    path.write_text(json.dumps(raw), encoding="utf-8")
    m = load_manifest(path)
    resolved = resolve_manifest_sources(m)
    assert resolved[0].source.user_id == "u1"
    assert resolved[0].source.platform == "local"


def test_manifest_v2_derives_external_id_for_web_url(tmp_path) -> None:
    raw = {
        "version": "2",
        "defaults": {"user_id": "u1", "platform": "web"},
        "sources": [
            {
                "title": "T",
                "web_url": "https://example.com/blog/post?utm_source=x#section",
            }
        ],
    }
    path = tmp_path / "manifest.json"
    path.write_text(json.dumps(raw), encoding="utf-8")
    m = load_manifest(path)
    resolved = resolve_manifest_sources(m)
    assert resolved[0].source.external_id == url_external_id(raw["sources"][0]["web_url"])


def test_manifest_v2_rejects_non_positive_max_items(tmp_path) -> None:
    raw = {
        "version": "2",
        "defaults": {"user_id": "u1", "platform": "web"},
        "sources": [{"title": "seed", "crawl_seed_url": "https://example.com/", "max_items": 0}],
    }
    path = tmp_path / "manifest.json"
    path.write_text(json.dumps(raw), encoding="utf-8")
    with pytest.raises(InvalidInputError):
        load_manifest(path)
