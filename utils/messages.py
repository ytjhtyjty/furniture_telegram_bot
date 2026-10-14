from contextlib import suppress
from html import escape

from aiogram.exceptions import TelegramBadRequest
from aiogram.types import InlineKeyboardMarkup, Message

from settings.config import ConfigBot


def contacts_block() -> str:
    lines = []
    if ConfigBot.CONTACT_PHONE:
        lines.append(f"📞 Телефон: {escape(ConfigBot.CONTACT_PHONE)}")
    if ConfigBot.CONTACT_WHATSAPP:
        lines.append(f"💬 WhatsApp: {escape(ConfigBot.CONTACT_WHATSAPP)}")
    if ConfigBot.CONTACT_TELEGRAM:
        lines.append(f"✈️ Telegram: {escape(ConfigBot.CONTACT_TELEGRAM)}")
    if ConfigBot.CONTACT_INSTAGRAM:
        lines.append(f"📸 Instagram: {escape(ConfigBot.CONTACT_INSTAGRAM)}")
    if not lines:
        return ""
    return "💬 <b>Для заказа этой мебели:</b>\n" + "\n".join(lines)


async def safe_edit_text(
    message: Message,
    text: str,
    reply_markup: InlineKeyboardMarkup | None = None,
) -> None:
    try:
        await message.edit_text(text, reply_markup=reply_markup)
    except TelegramBadRequest as e:
        if "message is not modified" in str(e):
            return
        await message.answer(text, reply_markup=reply_markup)
        with suppress(TelegramBadRequest):
            await message.delete()
