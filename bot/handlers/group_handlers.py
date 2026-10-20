import logging

from bot.max_platform import ChatType
from bot.max_platform import Command
from bot.max_platform import ChatMemberUpdated, Message

from bot.core import bot, group_router
from bot.utils.filters import GroupChatFilter

# Применяем фильтр групповых чатов к роутеру
group_router.message.filter(GroupChatFilter())
group_router.chat_member.filter(GroupChatFilter())


def is_group_chat(message: Message) -> bool:
    """Проверяет, является ли чат групповым"""
    return message.chat.type in [ChatType.GROUP, ChatType.SUPERGROUP]


@group_router.message(Command("show_id"))
async def handle_show_id(message: Message):
    """Обработчик команды /show_id - показывает ID чата и топика (только в групповых чатах)"""
    logging.info(f"Команда /show_id вызвана в чате {message.chat.type} (ID: {message.chat.id})")

    # Проверяем, что это групповой чат
    if not is_group_chat(message):
        user_id = message.from_user.id
        logging.info(f"Показываем ID пользователя: {user_id}")
        await message.reply(
            f"🏷️ Ваш ID: <code>{user_id}</code>\n\nЕсли вы хотите узнать информацию о чате, добавьте бота в групповой чат.")
        return

    chat_id = message.chat.id
    chat_title = message.chat.title if getattr(message.chat, "title", None) else "Группа"

    response = "📋 <b>Информация о чате:</b>\n\n"
    response += f"💬 <b>Название:</b> {chat_title}\n"
    response += f"🆔 <b>ID чата:</b> <code>{chat_id}</code>\n"
    response += "\nВ MAX нет топиков. Этот ID указывается в настройках команды как чат для отчётов.\n"

    await message.reply(response)
