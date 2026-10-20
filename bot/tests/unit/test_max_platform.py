import asyncio

from bot.max_platform.chat_ids import is_messenger_chat_id
from bot.max_platform.client import split_text
from bot.max_platform.filters import Command, CommandStart
from bot.max_platform.fsm import State, StatesGroup
from bot.max_platform.keyboards import InlineKeyboardButton, InlineKeyboardMarkup, markup_to_attachment
from bot.max_platform.router import Dispatcher, Router
from bot.max_platform.updates import parse_update


def test_bot_started_becomes_start_command():
    event = parse_update({
        "update_type": "bot_started",
        "chat_id": 10,
        "payload": "invite-code",
        "user": {"user_id": 5, "first_name": "Иван", "is_bot": False},
    })
    assert event.text == "/start invite-code"
    assert event.from_user.id == 5
    assert event.chat.type == "private"
    assert event.message_thread_id is None


def test_dialog_and_group_chat_types():
    dialog = parse_update({
        "update_type": "message_created",
        "message": {
            "sender": {"user_id": 5, "first_name": "Иван", "is_bot": False},
            "recipient": {"chat_id": 99, "chat_type": "dialog"},
            "body": {"mid": "mid.1", "text": "привет"},
        },
    })
    group = parse_update({
        "update_type": "message_created",
        "message": {
            "sender": {"user_id": 5, "first_name": "Иван", "is_bot": False},
            "recipient": {"chat_id": 77, "chat_type": "chat"},
            "body": {"mid": "mid.2", "text": "/show_id"},
        },
    })
    assert dialog.chat.type == "private"
    assert group.chat.type == "group"


def test_audio_keeps_url_and_transcription():
    event = parse_update({
        "update_type": "message_created",
        "message": {
            "sender": {"user_id": 5, "first_name": "Иван", "is_bot": False},
            "recipient": {"chat_id": 99, "chat_type": "dialog"},
            "body": {
                "mid": "mid.1",
                "text": None,
                "attachments": [{
                    "type": "audio",
                    "payload": {"url": "https://cdn.example/a.ogg", "transcription": "привет"},
                }],
            },
        },
    })
    assert event.voice.file_id == "https://cdn.example/a.ogg"
    assert event.voice.transcription == "привет"


def test_callback_payload_and_bot_message():
    event = parse_update({
        "update_type": "message_callback",
        "callback": {
            "callback_id": "cb1",
            "payload": "set_time_morning",
            "timestamp": 1,
            "user": {"user_id": 5, "first_name": "Иван", "is_bot": False},
        },
        "message": {
            "sender": {"user_id": 1, "first_name": "Bot", "is_bot": True},
            "recipient": {"chat_id": 99, "chat_type": "dialog"},
            "body": {"mid": "mid.3", "text": "меню"},
        },
    })
    assert event.data == "set_time_morning"
    assert event.message.message_id == "mid.3"
    assert event.from_user.id == 5


def test_inline_keyboard_attachment():
    markup = InlineKeyboardMarkup(inline_keyboard=[[
        InlineKeyboardButton(text="Да", callback_data="yes"),
        InlineKeyboardButton(text="Документация", url="https://dev.max.ru/docs-api"),
    ]])
    attachment = markup_to_attachment(markup)
    row = attachment["payload"]["buttons"][0]
    assert attachment["type"] == "inline_keyboard"
    assert row[0] == {"type": "callback", "text": "Да", "payload": "yes"}
    assert row[1]["type"] == "link"
    assert row[1]["url"] == "https://dev.max.ru/docs-api"


def test_chat_id_accepts_max_positive_and_legacy_minus():
    assert is_messenger_chat_id("123456789")
    assert is_messenger_chat_id("-1001234567890")
    assert not is_messenger_chat_id("abc")
    assert not is_messenger_chat_id("")


def test_text_splits_at_4000():
    assert split_text("a" * 4000) == ["a" * 4000]
    parts = split_text("a" * 4001)
    assert "".join(parts) == "a" * 4001
    assert all(len(part) <= 4000 for part in parts)


def test_dispatcher_start_then_state():
    class Reg(StatesGroup):
        waiting_for_name = State()

    router = Router()
    seen = {}

    @router.message(CommandStart())
    async def start(message, state):
        seen["start"] = message.text
        await state.set_state(Reg.waiting_for_name)

    @router.message(Reg.waiting_for_name)
    async def name(message, state):
        seen["name"] = message.text

    dispatcher = Dispatcher()
    dispatcher.include_router(router)
    started = parse_update({
        "update_type": "bot_started",
        "chat_id": 10,
        "user": {"user_id": 5, "first_name": "Иван", "is_bot": False},
    })
    named = parse_update({
        "update_type": "message_created",
        "message": {
            "sender": {"user_id": 5, "first_name": "Иван", "is_bot": False},
            "recipient": {"chat_id": 10, "chat_type": "dialog"},
            "body": {"mid": "mid.9", "text": "Иван И."},
        },
    })

    async def run():
        await dispatcher.feed(started)
        await dispatcher.feed(named)

    asyncio.run(run())
    assert seen["start"] == "/start"
    assert seen["name"] == "Иван И."


def test_command_filter_ignores_bot_suffix():
    event = parse_update({
        "update_type": "message_created",
        "message": {
            "sender": {"user_id": 5, "first_name": "Иван", "is_bot": False},
            "recipient": {"chat_id": 77, "chat_type": "chat"},
            "body": {"mid": "mid.2", "text": "/show_id@dailybot"},
        },
    })

    async def check():
        return await Command("show_id")(event)

    assert asyncio.run(check()) is True
