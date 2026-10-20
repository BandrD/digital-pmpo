import inspect
import logging

from bot.max_platform.fsm import FSMContext, MemoryStorage, State


class _Observer:
    def __init__(self):
        self.outer_filters = []
        self.handlers = []

    def filter(self, handler_filter):
        self.outer_filters.append(handler_filter)

    def __call__(self, *filters):
        def decorator(func):
            self.handlers.append((filters, func))
            return func

        return decorator


class Router:
    def __init__(self):
        self.message = _Observer()
        self.callback_query = _Observer()
        self.chat_member = _Observer()


class _FsmFacade:
    def __init__(self, storage: MemoryStorage):
        self.storage = storage


class Dispatcher:
    def __init__(self, storage: MemoryStorage | None = None):
        self.storage = storage or MemoryStorage()
        self.fsm = _FsmFacade(self.storage)
        self.routers: list[Router] = []
        self.bot = None

    def include_router(self, router: Router):
        self.routers.append(router)

    async def feed(self, event):
        kind = "callback_query" if event.__class__.__name__ == "CallbackQuery" else "message"
        user = getattr(event, "from_user", None)
        user_id = getattr(user, "id", None)
        for router in self.routers:
            observer = getattr(router, kind)
            if not await self._outer_ok(observer, event):
                continue
            for filters, handler in observer.handlers:
                if await self._filters_ok(filters, event, user_id):
                    await self._call(handler, event, user_id)
                    return

    async def _outer_ok(self, observer: _Observer, event) -> bool:
        for handler_filter in observer.outer_filters:
            if not await _run_filter(handler_filter, event):
                return False
        return True

    async def _filters_ok(self, filters, event, user_id) -> bool:
        for handler_filter in filters:
            if isinstance(handler_filter, State):
                current = await self.storage.get_state(user_id)
                if current != handler_filter.state:
                    return False
                continue
            if not await _run_filter(handler_filter, event):
                return False
        return True

    async def _call(self, handler, event, user_id):
        kwargs = {}
        signature = inspect.signature(handler)
        if "state" in signature.parameters:
            kwargs["state"] = FSMContext(self.storage, user_id)
        try:
            await handler(event, **kwargs)
        except Exception:
            logging.exception("Ошибка обработчика %s", getattr(handler, "__name__", handler))

    async def start_polling(self, bot):
        self.bot = bot
        bot.bind_dispatcher(self)
        try:
            await bot.poll(self)
        finally:
            await bot.close()


async def _run_filter(handler_filter, event) -> bool:
    result = handler_filter(event)
    if inspect.isawaitable(result):
        result = await result
    return bool(result)
