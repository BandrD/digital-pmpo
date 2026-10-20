class State:
    def __init__(self):
        self._group = ""
        self._name = ""

    def __set_name__(self, owner, name):
        self._group = owner.__name__
        self._name = name

    @property
    def state(self) -> str:
        return f"{self._group}:{self._name}"

    def __eq__(self, other):
        if isinstance(other, State):
            return self.state == other.state
        if isinstance(other, str):
            return self.state == other
        return False

    def __hash__(self):
        return hash(self.state)

    def __repr__(self):
        return f"State({self.state})"


class StatesGroup:
    def __init_subclass__(cls, **kwargs):
        super().__init_subclass__(**kwargs)
        for name, value in cls.__dict__.items():
            if isinstance(value, State):
                value._group = cls.__name__
                value._name = name


class MemoryStorage:
    def __init__(self):
        self._states: dict[str, str | None] = {}
        self._data: dict[str, dict] = {}

    @staticmethod
    def _key(user_id) -> str:
        return str(user_id)

    async def set_state(self, user_id, chat_id=None, state=None):
        """Совместимо с вызовом storage.set_state(user_id, chat_id, state) из weekly_plan_handlers."""
        if state is not None and chat_id is not None and not _is_state(chat_id) and _is_state(state):
            key = self._key(user_id)
            value = state
        elif _is_state(chat_id) and state is None:
            key = self._key(user_id)
            value = chat_id
        else:
            key = self._key(user_id)
            value = state
        self._states[key] = value.state if isinstance(value, State) else value

    async def get_state(self, user_id) -> str | None:
        return self._states.get(self._key(user_id))

    async def update_data(self, user_id, **kwargs):
        bucket = self._data.setdefault(self._key(user_id), {})
        bucket.update(kwargs)

    async def get_data(self, user_id) -> dict:
        return dict(self._data.get(self._key(user_id), {}))

    async def set_data(self, user_id, data: dict):
        self._data[self._key(user_id)] = dict(data or {})

    async def clear(self, user_id):
        self._states.pop(self._key(user_id), None)
        self._data.pop(self._key(user_id), None)


def _is_state(value) -> bool:
    return isinstance(value, State)


class FSMContext:
    def __init__(self, storage: MemoryStorage, user_id):
        self.storage = storage
        self.user_id = user_id

    async def set_state(self, state=None):
        await self.storage.set_state(self.user_id, state=state)

    async def get_state(self):
        return await self.storage.get_state(self.user_id)

    async def update_data(self, **kwargs):
        await self.storage.update_data(self.user_id, **kwargs)

    async def get_data(self) -> dict:
        return await self.storage.get_data(self.user_id)

    async def set_data(self, data: dict):
        await self.storage.set_data(self.user_id, data)

    async def clear(self):
        await self.storage.clear(self.user_id)
