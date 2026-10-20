from bot.config import MAX_BOT_TOKEN
from bot.max_platform import Bot, Dispatcher, MemoryStorage, Router

bot = Bot(token=MAX_BOT_TOKEN)
storage = MemoryStorage()
dp = Dispatcher(storage=storage)
router = Router()
group_router = Router()
