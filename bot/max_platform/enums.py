class ParseMode:
    HTML = "HTML"
    MARKDOWN = "Markdown"


class ChatType:
    """Типы, которые уже проверяет код бота.

    MAX отдаёт dialog | chat | channel. При разборе апдейта dialog становится
    private, chat — group. SUPERGROUP оставлен, чтобы старые сравнения не падали,
    но новые апдейты его не получают: топиков форума в MAX нет.
    """

    PRIVATE = "private"
    GROUP = "group"
    SUPERGROUP = "supergroup"
    CHANNEL = "channel"
