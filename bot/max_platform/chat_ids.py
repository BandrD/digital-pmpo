def is_messenger_chat_id(value: str) -> bool:
    """ID чата MAX — положительное число. Ведущий минус ещё принимается: так были устроены id групп Telegram."""
    if not isinstance(value, str):
        return False
    raw = value.strip()
    digits = raw[1:] if raw.startswith("-") else raw
    return digits.isdigit() and 1 <= len(digits) <= 18
