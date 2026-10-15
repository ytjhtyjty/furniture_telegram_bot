import logging
from typing import Any, Awaitable, Callable

from aiogram import BaseMiddleware
from aiogram.types import Update

logger = logging.getLogger("updates")


def _describe(update: Update) -> str:
    if update.callback_query is not None:
        return f"нажата кнопка {update.callback_query.data!r}"
    msg = update.message
    if msg is not None:
        if msg.text:
            if msg.text.startswith("/"):
                return f"команда {msg.text.split()[0]}"
            return f"текст ({len(msg.text)} симв.)"
        return f"сообщение: {msg.content_type}"
    return "другое событие"


class LoggingMiddleware(BaseMiddleware):

    async def __call__(
        self,
        handler: Callable[[Update, dict[str, Any]], Awaitable[Any]],
        event: Update,
        data: dict[str, Any],
    ) -> Any:
        user = data.get("event_from_user")
        if user:
            who = f"{user.id} (@{user.username})" if user.username else str(user.id)
        else:
            who = "?"
        logger.info("Пользователь %s: %s", who, _describe(event))
        return await handler(event, data)
