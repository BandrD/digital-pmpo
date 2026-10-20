from bot.max_platform.enums import ChatType


_CHAT_TYPES = {
    "dialog": ChatType.PRIVATE,
    "chat": ChatType.GROUP,
    "channel": ChatType.CHANNEL,
    "private": ChatType.PRIVATE,
    "group": ChatType.GROUP,
    "supergroup": ChatType.SUPERGROUP,
}


class User:
    def __init__(self, data: dict | None):
        data = data or {}
        self.id = data.get("user_id")
        self.is_bot = bool(data.get("is_bot"))
        self.first_name = data.get("first_name") or data.get("name") or ""
        self.last_name = data.get("last_name") or ""
        self.username = data.get("username") or data.get("name") or ""
        self.language_code = data.get("user_locale")

    @property
    def full_name(self) -> str:
        return f"{self.first_name} {self.last_name}".strip()


class Chat:
    def __init__(self, chat_id, chat_type: str, title: str | None = None):
        self.id = chat_id
        self.type = _CHAT_TYPES.get(chat_type, chat_type)
        self.title = title


class Voice:
    def __init__(self, file_id: str, transcription: str | None = None):
        self.file_id = file_id
        self.transcription = transcription


class Message:
    def __init__(
        self,
        *,
        message_id: str | None,
        chat: Chat,
        from_user: User | None,
        text: str | None = None,
        voice: Voice | None = None,
        bot=None,
    ):
        self.message_id = message_id
        self.chat = chat
        self.from_user = from_user
        self.text = text
        self.voice = voice
        self.bot = bot
        # Топиков форума в MAX нет. Атрибут оставлен: старый код читает его перед отправкой в тему.
        self.message_thread_id = None

    async def answer(self, text, **kwargs):
        return await self.bot.send_message(self.chat.id, text, _as_chat=True, **kwargs)

    async def reply(self, text, **kwargs):
        kwargs.setdefault("reply_to", self.message_id)
        return await self.answer(text, **kwargs)

    async def answer_photo(self, photo, caption: str | None = None, **kwargs):
        return await self.bot.send_photo(self.chat.id, photo, caption=caption, _as_chat=True, **kwargs)

    async def delete(self):
        if self.message_id:
            await self.bot.delete_message(self.chat.id, self.message_id)


class CallbackQuery:
    def __init__(self, *, callback_id: str, data: str, from_user: User, message: Message | None, bot=None):
        self.id = callback_id
        self.data = data or ""
        self.from_user = from_user
        self.message = message
        self.bot = bot

    async def answer(self, text: str | None = None, show_alert: bool = False, **_ignored):
        # show_alert в Telegram — модальное окно. В MAX notification всегда одноразовый тост.
        await self.bot.answer_callback(self.id, notification=text, chat_id=self._chat_id())

    def _chat_id(self):
        if self.message and self.message.chat:
            return self.message.chat.id
        return self.from_user.id if self.from_user else None


class ChatMemberUpdated:
    """Заглушка: отдельных событий вступления участника в стиле Telegram chat_member бот не обрабатывает."""

    def __init__(self, chat: Chat | None = None):
        self.chat = chat


def map_chat_type(raw: str | None) -> str:
    return _CHAT_TYPES.get(raw or "", raw or "private")
