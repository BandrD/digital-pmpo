class BaseFilter:
    async def __call__(self, event) -> bool:
        return True


class Command:
    def __init__(self, *commands: str):
        self.commands = [command.lstrip("/") for command in commands]

    async def __call__(self, event) -> bool:
        text = getattr(event, "text", None) or ""
        token = text.split()[0] if text else ""
        token = token.split("@", 1)[0]
        return any(token == f"/{name}" for name in self.commands)


class CommandStart(Command):
    def __init__(self):
        super().__init__("start")


class _Magic:
    def __init__(self, name: str):
        self.name = name

    def __eq__(self, other):
        return _Equals(self.name, other)

    def startswith(self, prefix: str):
        return _StartsWith(self.name, prefix)

    def in_(self, values):
        return _In(self.name, values)


class _Equals:
    def __init__(self, name: str, expected):
        self.name = name
        self.expected = expected

    async def __call__(self, event) -> bool:
        return getattr(event, self.name, None) == self.expected


class _StartsWith:
    def __init__(self, name: str, prefix: str):
        self.name = name
        self.prefix = prefix

    async def __call__(self, event) -> bool:
        value = getattr(event, self.name, None)
        return isinstance(value, str) and value.startswith(self.prefix)


class _In:
    def __init__(self, name: str, values):
        self.name = name
        self.values = set(values)

    async def __call__(self, event) -> bool:
        return getattr(event, self.name, None) in self.values


class _F:
    def __getattr__(self, name: str) -> _Magic:
        return _Magic(name)


F = _F()
