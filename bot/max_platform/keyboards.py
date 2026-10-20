class InlineKeyboardButton:
    def __init__(self, text: str, callback_data: str | None = None, url: str | None = None, **_ignored):
        self.text = text
        self.callback_data = callback_data
        self.url = url


class InlineKeyboardMarkup:
    def __init__(self, inline_keyboard: list):
        self.inline_keyboard = inline_keyboard


class ReplyKeyboardRemove:
    """В MAX нет постоянной клавиатуры под полем ввода. Объект оставлен, чтобы старые вызовы не падали."""

    def __init__(self, *args, **kwargs):
        pass


class BufferedInputFile:
    def __init__(self, file: bytes, filename: str | None = None):
        self.data = file if isinstance(file, (bytes, bytearray)) else bytes(file)
        self.filename = filename or "file.bin"


class FSInputFile:
    def __init__(self, path: str, filename: str | None = None):
        self.path = path
        self.filename = filename or os_path_name(path)

    def read(self) -> bytes:
        with open(self.path, "rb") as handle:
            return handle.read()


def os_path_name(path: str) -> str:
    return path.replace("\\", "/").rstrip("/").split("/")[-1]


def markup_to_attachment(markup) -> dict | None:
    if markup is None or isinstance(markup, ReplyKeyboardRemove):
        return None
    rows = getattr(markup, "inline_keyboard", None)
    if not rows:
        return None
    buttons = []
    for row in rows:
        built = []
        for button in row:
            text = (button.text or "")[:128] or " "
            if getattr(button, "url", None):
                built.append({"type": "link", "text": text, "url": button.url[:2048]})
            else:
                payload = button.callback_data or ""
                built.append({"type": "callback", "text": text, "payload": payload[:1024]})
        if built:
            buttons.append(built[:7])
    if not buttons:
        return None
    return {"type": "inline_keyboard", "payload": {"buttons": buttons[:30]}}
