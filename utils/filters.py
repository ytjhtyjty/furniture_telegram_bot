from aiogram.filters import BaseFilter
from aiogram.types import Message, CallbackQuery

from settings.config import ConfigBot


class IsAdmin(BaseFilter):
    async def __call__(self, event: Message | CallbackQuery) -> bool:
        if not event.from_user:
            return False
        return event.from_user.id in ConfigBot.ADMIN_IDS


class NotCommand(BaseFilter):

    async def __call__(self, message: Message) -> bool:
        return not (message.text or "").startswith("/")
