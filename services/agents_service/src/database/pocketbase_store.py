"""PocketBase-backed Store implementation for local dev.

PocketBase record IDs are not UUIDs. To preserve the logical schema (UUID PKs)
from BLUEPRINT.md, we store UUIDs in explicit `*_uuid` fields and map them back
to `id` / `agent_id` / `source_id` keys in returned dictionaries.
"""

from __future__ import annotations

import asyncio
from dataclasses import dataclass
from typing import Any, Literal
from uuid import UUID, uuid4

import httpx


class PocketBaseError(RuntimeError):
    pass


class PocketBaseAuthError(PocketBaseError):
    pass


def _escape_filter_value(value: str) -> str:
    # PocketBase uses a simple string-based filter language with double quotes.
    return value.replace("\\", "\\\\").replace('"', '\\"')


def _or_equals(field: str, values: list[str]) -> str:
    parts = [f'{field}="{_escape_filter_value(v)}"' for v in values if v]
    return " || ".join(parts)


@dataclass(frozen=True)
class PocketBaseConfig:
    url: str
    email: str
    password: str


class PocketBaseStore:
    """Async PocketBase client with just enough CRUD for agents_service."""

    def __init__(
        self,
        *,
        config: PocketBaseConfig,
        http_client: httpx.AsyncClient | None = None,
        request_timeout_s: float = 15.0,
    ) -> None:
        self._config = config
        self._http = http_client or httpx.AsyncClient(
            base_url=config.url.rstrip("/"),
            timeout=request_timeout_s,
        )
        self._token: str | None = None
        self._token_lock = asyncio.Lock()

    async def aclose(self) -> None:
        await self._http.aclose()

    async def _auth(self) -> str:
        if self._token:
            return self._token
        async with self._token_lock:
            if self._token:
                return self._token

            # PocketBase has evolved auth routes. Try both to be resilient.
            routes: list[Literal["/api/superusers/auth-with-password", "/api/admins/auth-with-password"]] = [
                "/api/superusers/auth-with-password",
                "/api/admins/auth-with-password",
            ]

            last_error: str | None = None
            for route in routes:
                for payload in (
                    {"identity": self._config.email, "password": self._config.password},
                    {"email": self._config.email, "password": self._config.password},
                ):
                    resp = await self._http.post(route, json=payload)
                    if resp.status_code == 200:
                        data = resp.json()
                        token = data.get("token")
                        if not token:
                            raise PocketBaseAuthError("PocketBase auth succeeded but token missing")
                        self._token = str(token)
                        return self._token
                    last_error = f"{route} {resp.status_code}: {resp.text}"

            raise PocketBaseAuthError(f"PocketBase auth failed: {last_error}")

    async def _request(
        self,
        method: str,
        path: str,
        *,
        params: dict[str, Any] | None = None,
        json: dict[str, Any] | None = None,
    ) -> httpx.Response:
        token = await self._auth()
        resp = await self._http.request(
            method,
            path,
            params=params,
            json=json,
            headers={"Authorization": f"Bearer {token}"},
        )
        return resp

    async def _list_records(
        self,
        collection: str,
        *,
        filter_expr: str | None = None,
        per_page: int = 200,
        sort: str | None = None,
    ) -> list[dict[str, Any]]:
        items: list[dict[str, Any]] = []
        page = 1
        while True:
            params: dict[str, Any] = {"page": page, "perPage": per_page}
            if filter_expr:
                params["filter"] = filter_expr
            if sort:
                params["sort"] = sort
            resp = await self._request(
                "GET", f"/api/collections/{collection}/records", params=params
            )
            if resp.status_code != 200:
                raise PocketBaseError(
                    f"PocketBase list failed collection={collection} status={resp.status_code} body={resp.text}"
                )
            payload = resp.json()
            page_items = payload.get("items") or []
            if not isinstance(page_items, list):
                break
            items.extend(page_items)
            total_pages = int(payload.get("totalPages") or 1)
            if page >= total_pages:
                break
            page += 1
        return items

    async def _first_record(
        self, collection: str, *, filter_expr: str
    ) -> dict[str, Any] | None:
        resp = await self._request(
            "GET",
            f"/api/collections/{collection}/records",
            params={"page": 1, "perPage": 1, "filter": filter_expr},
        )
        if resp.status_code != 200:
            raise PocketBaseError(
                f"PocketBase query failed collection={collection} status={resp.status_code} body={resp.text}"
            )
        payload = resp.json()
        items = payload.get("items") or []
        if not items:
            return None
        return items[0]

    async def _create_record(
        self, collection: str, *, payload: dict[str, Any]
    ) -> dict[str, Any]:
        resp = await self._request(
            "POST", f"/api/collections/{collection}/records", json=payload
        )
        if resp.status_code not in {200, 201}:
            raise PocketBaseError(
                f"PocketBase create failed collection={collection} status={resp.status_code} body={resp.text}"
            )
        return resp.json()

    async def _update_record(
        self, collection: str, record_id: str, *, payload: dict[str, Any]
    ) -> dict[str, Any]:
        resp = await self._request(
            "PATCH",
            f"/api/collections/{collection}/records/{record_id}",
            json=payload,
        )
        if resp.status_code != 200:
            raise PocketBaseError(
                f"PocketBase update failed collection={collection} status={resp.status_code} body={resp.text}"
            )
        return resp.json()

    async def _upsert_by_unique(
        self,
        collection: str,
        *,
        unique_field: str,
        unique_value: str,
        create_payload: dict[str, Any],
        update_payload: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        existing = await self._first_record(
            collection,
            filter_expr=f'{unique_field}="{_escape_filter_value(unique_value)}"',
        )
        if existing is None:
            return await self._create_record(collection, payload=create_payload)
        if update_payload:
            return await self._update_record(
                collection, str(existing["id"]), payload=update_payload
            )
        return existing

    # ---- Store interface (runtime paths) ----

    async def get_agent(self, agent_id: UUID) -> dict[str, Any] | None:
        rec = await self._first_record(
            "agents", filter_expr=f'uuid="{_escape_filter_value(str(agent_id))}"'
        )
        return _map_agent(rec) if rec else None

    async def get_agent_by_matrix_id(self, matrix_user_id: str) -> dict[str, Any] | None:
        rec = await self._first_record(
            "agents",
            filter_expr=f'matrix_user_id="{_escape_filter_value(matrix_user_id)}"',
        )
        return _map_agent(rec) if rec else None

    async def is_profile_room(self, matrix_room_id: str) -> bool:
        rec = await self._first_record(
            "profile_rooms",
            filter_expr=f'matrix_room_id="{_escape_filter_value(matrix_room_id)}"',
        )
        return rec is not None

    async def get_agent_emos_config(self, agent_id: UUID) -> dict[str, Any] | None:
        rec = await self._first_record(
            "agent_emos_config",
            filter_expr=f'agent_uuid="{_escape_filter_value(str(agent_id))}"',
        )
        if not rec:
            return None
        return {
            "agent_id": str(agent_id),
            "emos_base_url": rec.get("emos_base_url"),
            "emos_api_key_encrypted": rec.get("emos_api_key_encrypted"),
            "emos_api_key": rec.get("emos_api_key"),
            "tenant_prefix": rec.get("tenant_prefix"),
        }

    async def get_segments_by_ids(self, segment_ids: list[UUID]) -> list[dict[str, Any]]:
        ids = [str(i) for i in segment_ids]
        if not ids:
            return []
        filter_expr = _or_equals("uuid", ids)
        if not filter_expr:
            return []
        recs = await self._list_records("segments", filter_expr=filter_expr, per_page=200)
        return [_map_segment(rec) for rec in recs]

    async def get_sources_by_emos_group_ids(self, emos_group_ids: list[str]) -> list[dict[str, Any]]:
        if not emos_group_ids:
            return []
        filter_expr = _or_equals("emos_group_id", emos_group_ids)
        if not filter_expr:
            return []
        recs = await self._list_records("sources", filter_expr=filter_expr, per_page=200)
        return [_map_source(rec) for rec in recs]

    async def get_segments_by_source_ids(self, source_ids: list[str]) -> list[dict[str, Any]]:
        if not source_ids:
            return []
        filter_expr = _or_equals("source_uuid", source_ids)
        if not filter_expr:
            return []
        recs = await self._list_records("segments", filter_expr=filter_expr, per_page=200, sort="seq")
        return [_map_segment(rec) for rec in recs]

    async def get_segments_for_agent(self, agent_id: UUID) -> list[dict[str, Any]]:
        recs = await self._list_records(
            "segments",
            filter_expr=f'agent_uuid="{_escape_filter_value(str(agent_id))}"',
            per_page=200,
            sort="seq",
        )
        return [_map_segment(rec) for rec in recs]

    async def save_chat_history(self, record: dict[str, Any]) -> dict[str, Any]:
        # Accept the same dict shape as Supabase insert.
        payload = dict(record)
        payload.setdefault("uuid", str(uuid4()))
        if "sender_agent_id" in payload and payload["sender_agent_id"] is not None:
            payload["sender_agent_uuid"] = str(payload.pop("sender_agent_id"))
        if "citations" in payload and payload["citations"] is None:
            payload["citations"] = []
        created = await self._create_record("chat_history", payload=payload)
        return created

    # ---- Bootstrap helpers (write paths) ----

    async def upsert_agent(
        self,
        *,
        agent_uuid: UUID,
        kind: str,
        display_name: str,
        matrix_user_id: str,
        persona_prompt: str,
        llm_model: str,
        is_active: bool = True,
    ) -> dict[str, Any]:
        create_payload = {
            "uuid": str(agent_uuid),
            "kind": kind,
            "display_name": display_name,
            "matrix_user_id": matrix_user_id,
            "persona_prompt": persona_prompt,
            "llm_model": llm_model,
            "is_active": bool(is_active),
        }
        update_payload = dict(create_payload)
        rec = await self._upsert_by_unique(
            "agents",
            unique_field="uuid",
            unique_value=str(agent_uuid),
            create_payload=create_payload,
            update_payload=update_payload,
        )
        return _map_agent(rec)

    async def upsert_agent_emos_config(
        self,
        *,
        agent_uuid: UUID,
        emos_base_url: str,
        tenant_prefix: str,
        emos_api_key: str | None = None,
    ) -> dict[str, Any]:
        create_payload = {
            "agent_uuid": str(agent_uuid),
            "emos_base_url": emos_base_url,
            "tenant_prefix": tenant_prefix,
            "emos_api_key": emos_api_key,
        }
        update_payload = dict(create_payload)
        rec = await self._upsert_by_unique(
            "agent_emos_config",
            unique_field="agent_uuid",
            unique_value=str(agent_uuid),
            create_payload=create_payload,
            update_payload=update_payload,
        )
        return rec

    async def upsert_profile_room(
        self, *, agent_uuid: UUID, matrix_room_id: str
    ) -> dict[str, Any]:
        create_payload = {"agent_uuid": str(agent_uuid), "matrix_room_id": matrix_room_id}
        update_payload = dict(create_payload)
        rec = await self._upsert_by_unique(
            "profile_rooms",
            unique_field="agent_uuid",
            unique_value=str(agent_uuid),
            create_payload=create_payload,
            update_payload=update_payload,
        )
        return rec

    async def upsert_source(
        self,
        *,
        agent_uuid: UUID,
        emos_group_id: str,
        platform: str,
        external_id: str,
        external_url: str | None,
        title: str,
        author: str | None = None,
        published_at: str | None = None,
        raw_meta: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        create_payload = {
            "uuid": str(uuid4()),
            "agent_uuid": str(agent_uuid),
            "emos_group_id": emos_group_id,
            "platform": platform,
            "external_id": external_id,
            "external_url": external_url,
            "title": title,
            "author": author,
            "published_at": published_at,
            "raw_meta": raw_meta or {},
        }

        update_payload = dict(create_payload)
        update_payload.pop("uuid", None)
        rec = await self._upsert_by_unique(
            "sources",
            unique_field="emos_group_id",
            unique_value=emos_group_id,
            create_payload=create_payload,
            update_payload=update_payload,
        )
        return _map_source(rec)

    async def upsert_segment(
        self,
        *,
        agent_uuid: UUID,
        source_uuid: UUID,
        emos_message_id: str,
        platform: str,
        seq: int,
        text: str,
        sha256: str,
        speaker: str | None = None,
        start_ms: int | None = None,
        end_ms: int | None = None,
        source_title: str | None = None,
        source_url: str | None = None,
        matrix_event_id: str | None = None,
    ) -> dict[str, Any]:
        create_payload = {
            "uuid": str(uuid4()),
            "agent_uuid": str(agent_uuid),
            "source_uuid": str(source_uuid),
            "emos_message_id": emos_message_id,
            "platform": platform,
            "seq": int(seq),
            "text": text,
            "sha256": sha256,
            "speaker": speaker,
            "start_ms": start_ms,
            "end_ms": end_ms,
            "source_title": source_title,
            "source_url": source_url,
            "matrix_event_id": matrix_event_id,
        }
        update_payload = dict(create_payload)
        update_payload.pop("uuid", None)
        rec = await self._upsert_by_unique(
            "segments",
            unique_field="emos_message_id",
            unique_value=emos_message_id,
            create_payload=create_payload,
            update_payload=update_payload,
        )
        return _map_segment(rec)

    async def list_agents(self, *, active_only: bool = False) -> list[dict[str, Any]]:
        filter_expr = None
        if active_only:
            filter_expr = "is_active=true"
        recs = await self._list_records("agents", filter_expr=filter_expr, per_page=200)
        return [_map_agent(rec) for rec in recs]

    async def get_profile_room_for_agent(self, agent_uuid: UUID) -> dict[str, Any] | None:
        rec = await self._first_record(
            "profile_rooms",
            filter_expr=f'agent_uuid="{_escape_filter_value(str(agent_uuid))}"',
        )
        if not rec:
            return None
        return {
            "agent_id": str(agent_uuid),
            "matrix_room_id": rec.get("matrix_room_id"),
        }

    async def get_agent_by_tenant_prefix(self, tenant_prefix: str) -> dict[str, Any] | None:
        rec = await self._first_record(
            "agent_emos_config",
            filter_expr=f'tenant_prefix="{_escape_filter_value(tenant_prefix)}"',
        )
        if not rec:
            return None
        agent_uuid = rec.get("agent_uuid")
        if not agent_uuid:
            return None
        return await self.get_agent(UUID(str(agent_uuid)))


def _map_agent(rec: dict[str, Any]) -> dict[str, Any]:
    return {
        "id": rec.get("uuid"),
        "kind": rec.get("kind"),
        "display_name": rec.get("display_name"),
        "matrix_user_id": rec.get("matrix_user_id"),
        "persona_prompt": rec.get("persona_prompt"),
        "llm_model": rec.get("llm_model"),
        "is_active": rec.get("is_active", True),
        "created_at": rec.get("created"),
    }


def _map_source(rec: dict[str, Any]) -> dict[str, Any]:
    return {
        "id": rec.get("uuid"),
        "agent_id": rec.get("agent_uuid"),
        "platform": rec.get("platform"),
        "external_id": rec.get("external_id"),
        "external_url": rec.get("external_url"),
        "title": rec.get("title"),
        "author": rec.get("author"),
        "published_at": rec.get("published_at"),
        "raw_meta": rec.get("raw_meta"),
        "emos_group_id": rec.get("emos_group_id"),
    }


def _map_segment(rec: dict[str, Any]) -> dict[str, Any]:
    return {
        "id": rec.get("uuid"),
        "source_id": rec.get("source_uuid"),
        "agent_id": rec.get("agent_uuid"),
        "platform": rec.get("platform"),
        "seq": rec.get("seq"),
        "text": rec.get("text"),
        "speaker": rec.get("speaker"),
        "start_ms": rec.get("start_ms"),
        "end_ms": rec.get("end_ms"),
        "sha256": rec.get("sha256"),
        "emos_message_id": rec.get("emos_message_id"),
        "source_title": rec.get("source_title"),
        "source_url": rec.get("source_url"),
        "matrix_event_id": rec.get("matrix_event_id"),
    }
