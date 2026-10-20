import asyncio
import logging
import time

from bot.max_platform.client import MaxClient, split_text
from bot.max_platform.keyboards import ReplyKeyboardRemove, markup_to_attachment
from bot.max_platform.types import User
from bot.max_platform.updates import parse_update

_IGNORED_SEND_KEYS = {
    "message_thread_id",
    "allow_sending_without_reply",
    "protect_content",
    "disable_notification",
}


class Bot:
    def __init__(self, token: str, parse_mode: str = "HTML"):
        self.client = MaxClient(token)
        self.default_parse_mode = parse_mode
        self._me: User | None = None
        self._group_ids: set[int] = set()
        self._user_ids: set[int] = set()
        self._answer_at: dict[int, float] = {}
        self._dispatcher = None

    def bind_dispatcher(self, dispatcher):
        self._dispatcher = dispatcher

    def remember_user(self, user_id):
        if user_id is None:
            return
        try:
            self._user_ids.add(int(user_id))
        except (TypeError, ValueError):
            return

    def remember_group(self, chat_id):
        if chat_id is None:
            return
        try:
            self._group_ids.add(int(chat_id))
        except (TypeError, ValueError):
            return

    async def me(self) -> User:
        if self._me is None:
            self._me = User(await self.client.get_me())
        return self._me

    async def close(self):
        await self.client.close()

    async def poll(self, dispatcher):
        marker = None
        logging.info("Long polling MAX: GET /updates")
        while True:
            started = time.monotonic()
            try:
                payload = await self.client.get_updates(marker)
                if payload.get("marker") is not None:
                    marker = payload.get("marker")
                for raw in payload.get("updates") or []:
                    await self._on_update(dispatcher, raw)
            except Exception:
                logging.exception("Ошибка long polling, пауза 1 с")
                await asyncio.sleep(1)
            elapsed = time.monotonic() - started
            if elapsed < 0.3:
                await asyncio.sleep(0.3 - elapsed)

    async def _on_update(self, dispatcher, raw: dict):
        parsed = parse_update(raw)
        if parsed is None:
            return
        if isinstance(parsed, tuple) and parsed and parsed[0] == "chat_seen":
            self.remember_group((parsed[1] or {}).get("chat_id"))
            return
        user = getattr(parsed, "from_user", None)
        if user is not None:
            self.remember_user(user.id)
        chat = getattr(parsed, "chat", None) or getattr(getattr(parsed, "message", None), "chat", None)
        if chat is not None and chat.type in {"group", "channel", "supergroup"}:
            self.remember_group(chat.id)
        parsed.bot = self
        message = getattr(parsed, "message", None)
        if message is not None:
            message.bot = self
        await dispatcher.feed(parsed)

    async def send_message(self, chat_id, text=None, **kwargs):
        if text is None:
            text = kwargs.pop("text", None)
        _as_chat = kwargs.pop("_as_chat", False)
        reply_to = kwargs.pop("reply_to", None)
        disable_preview = kwargs.pop("disable_web_page_preview", False) or kwargs.pop("disable_link_preview", False)
        parse_mode = kwargs.pop("parse_mode", self.default_parse_mode)
        reply_markup = kwargs.pop("reply_markup", None)
        if kwargs.get("message_thread_id") is not None:
            logging.info(
                "message_thread_id=%s пропущен: в MAX нет топиков, сообщение уйдёт в чат %s",
                kwargs.get("message_thread_id"),
                chat_id,
            )
        for key in list(kwargs):
            if key in _IGNORED_SEND_KEYS:
                kwargs.pop(key, None)
        if kwargs:
            logging.debug("Неиспользованные параметры send_message: %s", sorted(kwargs))
        attachment = markup_to_attachment(reply_markup)
        attachments = [attachment] if attachment else None
        fmt = _format(parse_mode)
        parts = split_text(text)
        sent = None
        for index, part in enumerate(parts):
            part_attachments = attachments if index == len(parts) - 1 else None
            target = await self._target(chat_id, as_chat=_as_chat)
            sent = await self.client.send_message(
                text=part,
                attachments=part_attachments,
                fmt=fmt,
                reply_to=reply_to if index == 0 else None,
                notify=True,
                disable_link_preview=bool(disable_preview),
                **target,
            )
        return _sent_message(sent, self, chat_id)

    async def edit_message_text(self, text=None, chat_id=None, message_id=None, **kwargs):
        if text is None:
            text = kwargs.pop("text", "")
        if message_id is None:
            message_id = kwargs.pop("message_id", None)
        kwargs.pop("chat_id", None)
        kwargs.pop("disable_web_page_preview", None)
        kwargs.pop("message_thread_id", None)
        parse_mode = kwargs.pop("parse_mode", self.default_parse_mode)
        reply_markup = kwargs.pop("reply_markup", None)
        if isinstance(reply_markup, ReplyKeyboardRemove) or reply_markup is None and "reply_markup" not in kwargs:
            # None в теле PUT сохраняет старые вложения. Пустой список снимает клавиатуру.
            attachment = markup_to_attachment(reply_markup)
            attachments = [attachment] if attachment else ([] if isinstance(reply_markup, ReplyKeyboardRemove) else None)
        else:
            attachment = markup_to_attachment(reply_markup)
            attachments = [attachment] if attachment else None
        await self.client.edit_message(
            str(message_id),
            text=text or "",
            attachments=attachments,
            fmt=_format(parse_mode),
        )

    async def send_photo(self, chat_id, photo, caption: str | None = None, **kwargs):
        _as_chat = kwargs.pop("_as_chat", False)
        kwargs.pop("message_thread_id", None)
        parse_mode = kwargs.pop("parse_mode", self.default_parse_mode)
        content, filename = await _read_file(photo)
        token = await self.client.upload("image", content, filename or "image.png")
        target = await self._target(chat_id, as_chat=_as_chat)
        return await self.client.send_message(
            text=caption,
            attachments=[{"type": "image", "payload": {"token": token}}],
            fmt=_format(parse_mode) if caption else None,
            reply_to=None,
            notify=True,
            disable_link_preview=False,
            **target,
        )

    async def send_document(self, chat_id=None, document=None, caption: str | None = None, **kwargs):
        if chat_id is None:
            chat_id = kwargs.pop("chat_id", None)
        if document is None:
            document = kwargs.pop("document", None)
        kwargs.pop("message_thread_id", None)
        parse_mode = kwargs.pop("parse_mode", self.default_parse_mode)
        reply_markup = kwargs.pop("reply_markup", None)
        content, filename = await _read_file(document)
        token = await self.client.upload("file", content, filename or "file.bin")
        attachments = [{"type": "file", "payload": {"token": token}}]
        keyboard = markup_to_attachment(reply_markup)
        if keyboard:
            attachments.append(keyboard)
        target = await self._target(chat_id, as_chat=False)
        return await self.client.send_message(
            text=caption,
            attachments=attachments,
            fmt=_format(parse_mode) if caption else None,
            reply_to=None,
            notify=True,
            disable_link_preview=False,
            **target,
        )

    async def delete_message(self, chat_id, message_id):
        if not message_id:
            return None
        return await self.client.delete_message(str(message_id))

    async def answer_callback(self, callback_id: str, notification: str | None = None, chat_id=None):
        if not callback_id:
            return None
        await self._throttle_answer(chat_id)
        return await self.client.answer_callback(callback_id, notification=notification)

    async def _throttle_answer(self, chat_id):
        if chat_id is None:
            return
        try:
            key = int(chat_id)
        except (TypeError, ValueError):
            return
        last = self._answer_at.get(key, 0)
        wait = 0.5 - (time.monotonic() - last)
        if wait > 0:
            await asyncio.sleep(wait)
        self._answer_at[key] = time.monotonic()

    async def _target(self, chat_id, *, as_chat: bool) -> dict:
        numeric = int(chat_id)
        if as_chat or numeric in self._group_ids:
            return {"chat_id": numeric}
        if numeric in self._user_ids:
            return {"user_id": numeric}
        if await _is_team_chat(numeric):
            self._group_ids.add(numeric)
            return {"chat_id": numeric}
        return {"user_id": numeric}


def _format(parse_mode) -> str | None:
    if not parse_mode:
        return None
    value = str(parse_mode).lower()
    if value == "html":
        return "html"
    if value == "markdown":
        return "markdown"
    return None


async def _read_file(file_obj) -> tuple[bytes, str]:
    if hasattr(file_obj, "data"):
        return bytes(file_obj.data), getattr(file_obj, "filename", None) or "file.bin"
    if hasattr(file_obj, "read"):
        data = file_obj.read()
        if asyncio.iscoroutine(data):
            data = await data
        return data, getattr(file_obj, "filename", None) or "file.bin"
    if isinstance(file_obj, (bytes, bytearray)):
        return bytes(file_obj), "file.bin"
    raise TypeError(f"Неизвестный файл для отправки: {type(file_obj)}")


def _sent_message(payload, bot, chat_id):
    from bot.max_platform.types import Chat, Message

    raw = payload if isinstance(payload, dict) else {}
    message = raw.get("message") if isinstance(raw.get("message"), dict) else raw
    body = message.get("body") if isinstance(message, dict) else {}
    mid = body.get("mid") if isinstance(body, dict) else None
    if mid is None and isinstance(message, dict):
        mid = message.get("mid")
    return Message(message_id=mid, chat=Chat(chat_id, "private"), from_user=None, bot=bot)


async def _is_team_chat(chat_id: int) -> bool:
    try:
        from bot.core.database import db_is_known_team_chat

        return await db_is_known_team_chat(chat_id)
    except Exception:
        logging.debug("Не удалось проверить chat_id %s в teams", chat_id, exc_info=True)
        return False
