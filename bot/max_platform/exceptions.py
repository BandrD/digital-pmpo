"""Ошибки Bot API MAX. Имена Telegram* оставлены как алиасы: на них завязан retry в utils."""


class MaxAPIError(Exception):
    def __init__(self, message: str = "", status: int | None = None, code: str | None = None):
        super().__init__(message)
        self.status = status
        self.code = code


class MaxNetworkError(MaxAPIError):
    pass


class MaxServerError(MaxAPIError):
    pass


class MaxNotFound(MaxAPIError):
    pass


class MaxForbiddenError(MaxAPIError):
    pass


class AttachmentNotReady(MaxAPIError):
    pass


TelegramAPIError = MaxAPIError
TelegramNetworkError = MaxNetworkError
TelegramServerError = MaxServerError
TelegramNotFound = MaxNotFound
TelegramForbiddenError = MaxForbiddenError
