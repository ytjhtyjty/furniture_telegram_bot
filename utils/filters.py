from aiogram.filters import BaseFilter
from aiogram.types import Message, CallbackQuery

from settings.config import ConfigBot


class IsAdmin(BaseFilter):
    async def __call__(self, event: Message | CallbackQuery) -> bool:
        return event.from_user.id in ConfigBot.ADMIN_IDS