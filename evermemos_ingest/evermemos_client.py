from __future__ import annotations

import asyncio
from datetime import datetime, timezone
from typing import Any, Awaitable, Callable

import httpx

from .errors import EMOSAuthError, EMOSNetworkError, EMOSServerError, EMOSValidationError


class EverMemOSClient:
    def __init__(
        self,
        base_url: str,
        *,
        api_key: str | None = None,
        timeout: float = 15.0,
        retries: int = 3,
        sdk_client: Any | None = None,
    ):
        self.base_url = base_url.rstrip("/")
        self.retries = retries
        self.headers: dict[str, str] = {}
        if api_key:
            self.headers["Authorization"] = f"Bearer {api_key}"

        if sdk_client is not None:
            self.client = sdk_client
            return

        from evermemos import AsyncEverMemOS  # type: ignore[import-not-found]

        http_client = httpx.AsyncClient(timeout=timeout, trust_env=False)
        self.client = AsyncEverMemOS(
            api_key=api_key,
            base_url=self.base_url,
            timeout=timeout,
            max_retries=0,
            default_headers=self.headers or None,
            http_client=http_client,
        )

    async def aclose(self) -> None:
        close_fn = getattr(self.client, "close", None)
        if close_fn is None:
            return
        maybe_awaitable = close_fn()
        if asyncio.iscoroutine(maybe_awaitable):
            await maybe_awaitable

    async def memorize(self, payload: dict[str, Any]) -> dict[str, Any]:
        required = {
            "message_id": payload.get("message_id", ""),
            "create_time": payload.get("create_time") or datetime.now(tz=timezone.utc).isoformat(),
            "sender": payload.get("sender", ""),
            "content": payload.get("content", ""),
        }
        optional_keys = {"flush", "group_id", "group_name", "refer_list", "role", "sender_name"}
        optional = {key: payload[key] for key in optional_keys if key in payload}

        known = {**required, **optional}
        extra_body = {key: value for key, value in payload.items() if key not in known}

        return await self._run_with_retry(
            lambda: self.client.v0.memories.add(
                **known,
                extra_headers=self.headers or None,
                extra_body=extra_body or None,
            )
        )

    async def save_conversation_meta(self, *, group_id: str, source_meta: dict[str, Any]) -> dict[str, Any]:
        created_at = datetime.now(tz=timezone.utc).isoformat()
        payload = {
            "group_id": group_id,
            # Keep `scene` flexible; EverMemOS instances vary. This minimal scene is still useful for grouping.
            "scene": {"group_id": group_id},
            "scene_desc": {"extra": source_meta},
            "created_at": created_at,
        }

        return await self._run_with_retry(
            lambda: self.client.v0.memories.conversation_meta.create(
                created_at=created_at,
                scene=payload["scene"],
                scene_desc=payload.get("scene_desc"),
                tags=payload.get("tags"),
                user_details=payload.get("user_details"),
                extra_headers=self.headers or None,
                extra_body=payload,
            )
        )

    async def _run_with_retry(self, operation: Callable[[], Awaitable[Any]]) -> dict[str, Any]:
        for attempt in range(1, self.retries + 1):
            try:
                result = await operation()
                return self._normalize_result(result)
            except Exception as exc:  # noqa: BLE001
                if self._should_retry(exc) and attempt < self.retries:
                    await asyncio.sleep(2 ** (attempt - 1))
                    continue
                self._raise_mapped_error(exc)
        raise EMOSNetworkError("EverMemOS request failed after retries")

    def _normalize_result(self, result: Any) -> dict[str, Any]:
        if isinstance(result, dict):
            return result
        if hasattr(result, "to_dict"):
            value = result.to_dict()
            if isinstance(value, dict):
                return value
        if hasattr(result, "model_dump"):
            value = result.model_dump(mode="json")
            if isinstance(value, dict):
                return value
        return {"result": result}

    def _should_retry(self, exc: Exception) -> bool:
        class_name = exc.__class__.__name__
        if class_name in {"APIConnectionError", "APITimeoutError"}:
            return True
        status_code = self._extract_status_code(exc)
        return status_code is not None and status_code >= 500

    def _extract_status_code(self, exc: Exception) -> int | None:
        value = getattr(exc, "status_code", None)
        if isinstance(value, int):
            return value
        response = getattr(exc, "response", None)
        status = getattr(response, "status_code", None)
        return status if isinstance(status, int) else None

    def _extract_code(self, exc: Exception) -> str:
        body = getattr(exc, "body", None)
        if isinstance(body, dict):
            code = body.get("code")
            if isinstance(code, str):
                return code
        return ""

    def _extract_message(self, exc: Exception) -> str:
        body = getattr(exc, "body", None)
        if isinstance(body, dict):
            message = body.get("message")
            if isinstance(message, str) and message:
                return message
        message = getattr(exc, "message", None)
        if isinstance(message, str) and message:
            return message
        return str(exc)

    def _raise_mapped_error(self, exc: Exception) -> None:
        class_name = exc.__class__.__name__
        message = self._extract_message(exc)

        if class_name in {"APIConnectionError", "APITimeoutError"}:
            raise EMOSNetworkError(message) from exc

        status_code = self._extract_status_code(exc)
        code = self._extract_code(exc)

        if status_code in {401, 403} or code in {"UNAUTHORIZED", "FORBIDDEN"}:
            raise EMOSAuthError(message) from exc

        if class_name in {"BadRequestError", "UnprocessableEntityError"} or status_code in {400, 422} or code == "INVALID_PARAMETER":
            raise EMOSValidationError(message) from exc

        if status_code is not None and status_code >= 500:
            raise EMOSServerError(message) from exc

        raise EMOSServerError(message) from exc

