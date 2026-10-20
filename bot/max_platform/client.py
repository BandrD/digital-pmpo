import asyncio
import logging
from typing import Any

import aiohttp

from bot.max_platform.exceptions import (
    AttachmentNotReady,
    MaxAPIError,
    MaxForbiddenError,
    MaxNetworkError,
    MaxNotFound,
    MaxServerError,
)
from bot.max_platform.ssl_context import max_ssl_context

BASE_URL = "https://platform-api2.max.ru"
_MIN_POLL_GAP = 0.3


class MaxClient:
    def __init__(self, token: str):
        self.token = token or ""
        self._session: aiohttp.ClientSession | None = None

    async def session(self) -> aiohttp.ClientSession:
        if self._session is None or self._session.closed:
            timeout = aiohttp.ClientTimeout(total=100, sock_connect=20, sock_read=95)
            self._session = aiohttp.ClientSession(
                timeout=timeout,
                connector=aiohttp.TCPConnector(ssl=max_ssl_context()),
            )
        return self._session

    async def close(self):
        if self._session and not self._session.closed:
            await self._session.close()

    async def request(
        self,
        method: str,
        path: str,
        *,
        params: dict | None = None,
        json: dict | None = None,
        data=None,
        headers: dict | None = None,
        auth: bool = True,
    ) -> Any:
        if not self.token and auth:
            raise RuntimeError("Не задан токен бота MAX (MAX_BOT_TOKEN)")
        url = path if path.startswith("http") else f"{BASE_URL}{path}"
        req_headers = {}
        if auth:
            req_headers["Authorization"] = self.token
        if headers:
            req_headers.update(headers)
        if json is not None and "Content-Type" not in req_headers:
            req_headers["Content-Type"] = "application/json"
        query = {key: value for key, value in (params or {}).items() if value is not None}
        try:
            http = await self.session()
            async with http.request(method, url, params=query, json=json, data=data, headers=req_headers) as response:
                return await self._read(response)
        except aiohttp.ClientError as exc:
            raise MaxNetworkError(str(exc)) from exc
        except asyncio.TimeoutError as exc:
            raise MaxNetworkError(str(exc)) from exc

    async def _read(self, response: aiohttp.ClientResponse) -> Any:
        if response.status == 204:
            return {}
        try:
            payload = await response.json(content_type=None)
        except Exception:
            payload = {"message": await response.text()}
        if response.status < 400:
            return payload
        code = payload.get("code") if isinstance(payload, dict) else None
        message = payload.get("message") if isinstance(payload, dict) else str(payload)
        if code == "attachment.not.ready":
            raise AttachmentNotReady(message or "attachment.not.ready", response.status, code)
        if response.status == 404 or (code and "not.found" in str(code)):
            raise MaxNotFound(f"chat not found: {message}", response.status, code)
        if response.status == 403 or code == "chat.denied":
            raise MaxForbiddenError(f"bot was blocked: {message}", response.status, code)
        if response.status >= 500:
            raise MaxServerError(message or f"HTTP {response.status}", response.status, code)
        raise MaxAPIError(message or f"HTTP {response.status}", response.status, code)

    async def get_me(self) -> dict:
        payload = await self.request("GET", "/me")
        return payload if isinstance(payload, dict) else {}

    async def get_updates(self, marker: int | None, timeout: int = 25, limit: int = 100) -> dict:
        payload = await self.request(
            "GET",
            "/updates",
            params={"marker": marker, "timeout": timeout, "limit": limit},
        )
        if not isinstance(payload, dict):
            return {"updates": [], "marker": marker}
        payload.setdefault("updates", [])
        return payload

    async def send_message(self, *, text: str | None, attachments: list | None, fmt: str | None,
                           reply_to: str | None, notify: bool, disable_link_preview: bool,
                           chat_id: int | None = None, user_id: int | None = None) -> dict:
        body: dict[str, Any] = {"notify": notify}
        if text:
            body["text"] = text[:4000]
        if attachments:
            body["attachments"] = attachments
        if fmt:
            body["format"] = fmt
        if reply_to:
            body["link"] = {"type": "reply", "mid": str(reply_to)}
        params = {
            "chat_id": chat_id,
            "user_id": user_id,
            "disable_link_preview": "true" if disable_link_preview else None,
        }
        return await self._send_with_media_retry("POST", "/messages", params=params, json=body)

    async def edit_message(self, message_id: str, *, text: str | None, attachments: list | None, fmt: str | None) -> dict:
        body: dict[str, Any] = {}
        if text is not None:
            body["text"] = text[:4000]
        if attachments is None:
            body["attachments"] = None
        else:
            body["attachments"] = attachments
        if fmt:
            body["format"] = fmt
        return await self._send_with_media_retry(
            "PUT",
            "/messages",
            params={"message_id": message_id},
            json=body,
        )

    async def delete_message(self, message_id: str) -> dict:
        return await self.request("DELETE", "/messages", params={"message_id": message_id})

    async def answer_callback(self, callback_id: str, notification: str | None = None, message: dict | None = None) -> dict:
        body: dict[str, Any] = {}
        if notification:
            body["notification"] = notification
        if message:
            body["message"] = message
        return await self.request("POST", "/answers", params={"callback_id": callback_id}, json=body)

    async def upload(self, kind: str, content: bytes, filename: str) -> str:
        endpoint = await self.request("POST", "/uploads", params={"type": kind})
        upload_url = endpoint.get("url") if isinstance(endpoint, dict) else None
        if not upload_url:
            raise MaxAPIError(f"POST /uploads не вернул url: {endpoint}")
        token = endpoint.get("token") if isinstance(endpoint, dict) else None
        form = aiohttp.FormData()
        form.add_field("data", content, filename=filename or "file.bin")
        # Хост загрузки не platform-api2.max.ru и не требует корня Минцифры.
        # Тот же SSL-контекст всё равно доверяет публичным CA.
        uploaded = await self.request("POST", upload_url, data=form, auth=False)
        if isinstance(uploaded, dict):
            token = _extract_upload_token(uploaded) or token
        if not token:
            raise MaxAPIError(f"Загрузка {kind} не вернула token: {uploaded}")
        return token

    async def _send_with_media_retry(self, method: str, path: str, *, params: dict, json: dict) -> dict:
        delay = 0.5
        last_error: Exception | None = None
        for attempt in range(4):
            try:
                return await self.request(method, path, params=params, json=json)
            except AttachmentNotReady as exc:
                last_error = exc
                logging.info("Вложение ещё не готово, повтор %s через %.1f с", attempt + 1, delay)
                await asyncio.sleep(delay)
                delay *= 2
        raise last_error or AttachmentNotReady("attachment.not.ready")


def _extract_upload_token(payload: dict) -> str | None:
    if payload.get("token"):
        return payload["token"]
    photos = payload.get("photos")
    if isinstance(photos, dict):
        for value in photos.values():
            if isinstance(value, dict) and value.get("token"):
                return value["token"]
            if isinstance(value, str):
                return value
    for value in payload.values():
        if isinstance(value, dict) and value.get("token"):
            return value["token"]
    return None


def split_text(text: str | None, limit: int = 4000) -> list[str | None]:
    if text is None:
        return [None]
    if len(text) <= limit:
        return [text]
    parts: list[str] = []
    rest = text
    while len(rest) > limit:
        cut = rest.rfind("\n", 0, limit)
        if cut < limit // 2:
            cut = limit
        parts.append(rest[:cut])
        rest = rest[cut:].lstrip("\n")
    if rest:
        parts.append(rest)
    return parts
