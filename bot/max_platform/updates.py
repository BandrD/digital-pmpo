import logging

from bot.max_platform.types import CallbackQuery, Chat, Message, User, Voice, map_chat_type


def parse_update(raw: dict):
    """Превращает апдейт MAX в Message или CallbackQuery, которые уже ждут хендлеры."""
    if not isinstance(raw, dict):
        return None
    kind = raw.get("update_type")
    if kind == "message_created":
        return _message(raw.get("message") or {})
    if kind == "message_callback":
        return _callback(raw)
    if kind == "bot_started":
        return _started(raw)
    if kind in {"bot_added", "user_added"}:
        return ("chat_seen", raw)
    return None


def _user(data: dict | None) -> User:
    return User(data or {})


def _message(raw: dict) -> Message | None:
    if not raw:
        return None
    sender = raw.get("sender") or {}
    if sender.get("is_bot"):
        return None
    recipient = raw.get("recipient") or {}
    body = raw.get("body") or {}
    chat_type = map_chat_type(recipient.get("chat_type"))
    chat = Chat(recipient.get("chat_id"), chat_type, title=raw.get("title"))
    user = _user(sender)
    text = body.get("text")
    voice = None
    for attachment in body.get("attachments") or []:
        if attachment.get("type") != "audio":
            continue
        payload = attachment.get("payload") or {}
        voice = Voice(
            file_id=payload.get("url") or "",
            transcription=payload.get("transcription"),
        )
        break
    return Message(
        message_id=body.get("mid"),
        chat=chat,
        from_user=user,
        text=text,
        voice=voice,
    )


def _callback(raw: dict) -> CallbackQuery | None:
    callback = raw.get("callback") or {}
    user = _user(callback.get("user"))
    message = _message(raw.get("message") or {})
    if message is None and raw.get("message"):
        # Сообщение бота с клавиатурой: _message отбрасывает is_bot. Для callback оно нужно.
        message = _message_keep_bot(raw.get("message") or {})
    if message is None:
        chat_id = user.id
        message = Message(
            message_id=None,
            chat=Chat(chat_id, "private"),
            from_user=user,
            text=None,
        )
    return CallbackQuery(
        callback_id=callback.get("callback_id") or "",
        data=callback.get("payload") or "",
        from_user=user,
        message=message,
    )


def _message_keep_bot(raw: dict) -> Message | None:
    if not raw:
        return None
    recipient = raw.get("recipient") or {}
    body = raw.get("body") or {}
    sender = raw.get("sender") or {}
    chat = Chat(recipient.get("chat_id"), map_chat_type(recipient.get("chat_type")))
    return Message(
        message_id=body.get("mid"),
        chat=chat,
        from_user=_user(sender),
        text=body.get("text"),
    )


def _started(raw: dict) -> Message:
    user = _user(raw.get("user"))
    payload = raw.get("payload") or ""
    text = "/start" if not payload else f"/start {payload}"
    chat = Chat(raw.get("chat_id"), "private")
    logging.info("bot_started user=%s payload=%s", user.id, payload[:32])
    return Message(
        message_id=None,
        chat=chat,
        from_user=user,
        text=text,
    )
