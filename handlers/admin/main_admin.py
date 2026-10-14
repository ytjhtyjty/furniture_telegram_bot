from html import escape
from typing import Optional

from aiogram import Router, F, types
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from keyboard.keyboard_builder import make_row_inline_keyboards
from keyboard.button_template import admin_kb
from utils.messages import safe_edit_text

router = Router()


def _admin_panel_text(user: Optional[types.User]) -> str:
    greeting = ""
    if user is not None:
        greeting = f"Здравствуйте, <b>{escape(user.full_name)}</b> (<code>{user.id}</code>)\n\n"
    return (
        "👑 <b>Панель управления администратора</b>\n\n"
        f"{greeting}"
        "Выберите действие из меню ниже для управления каталогом магазина:"
    )


@router.message(Command("admin_panel"))
@router.callback_query(F.data == "settings_bot")
async def show_admin_panel(
    event: types.Message | types.CallbackQuery,
    state: Optional[FSMContext] = None,
    admin: Optional[types.User] = None,
):
    if state is not None:
        await state.clear()

    keyboard = make_row_inline_keyboards(admin_kb)

    if isinstance(event, types.CallbackQuery):
        await event.answer()
        await safe_edit_text(event.message, _admin_panel_text(event.from_user), keyboard)
    else:
        user = admin or (event.from_user if not event.from_user.is_bot else None)
        await event.answer(_admin_panel_text(user), reply_markup=keyboard)
