from aiogram import Router, F, types
from aiogram.filters import Command
from keyboard.keyboard_builder import make_row_inline_keyboards
from keyboard.button_template import admin_kb

router = Router()

# Срабатывает по команде /admin_panel или по callback "settings_bot"
@router.message(Command("admin_panel"))
@router.callback_query(F.data == "settings_bot")
async def show_admin_panel(event: types.Message | types.CallbackQuery):
    text = (
        "👑 <b>Панель управления администратора</b>\n\n"
        "Выберите действие из меню ниже для управления каталогом магазина:"
    )
    keyboard = make_row_inline_keyboards(admin_kb)

    if isinstance(event, types.CallbackQuery):
        try:
            await event.message.edit_text(text, reply_markup=keyboard)
        except Exception:
            await event.message.answer(text, reply_markup=keyboard)
        await event.answer()
    else:
        await event.answer(text, reply_markup=keyboard)