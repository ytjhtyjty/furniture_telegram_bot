from typing import Optional
from aiogram import Router, F, types
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from keyboard.keyboard_builder import make_row_inline_keyboards
from keyboard.button_template import admin_kb

router = Router()

# Срабатывает по команде /admin_panel или по callback "settings_bot"
@router.message(Command("admin_panel"))
@router.callback_query(F.data == "settings_bot")
async def show_admin_panel(event: types.Message | types.CallbackQuery, state: Optional[FSMContext] = None):
    if state is not None:
        await state.clear()

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


@router.callback_query(F.data == "cooperation_requests")
async def show_cooperation_requests(callback: types.CallbackQuery):
    await callback.answer()
    back_kb = make_row_inline_keyboards([("⬅️ Назад в админ-панель", "settings_bot")])
    text = (
        "🤝 <b>Заявки на сотрудничество</b>\n\n"
        "📭 На данный момент новых входящих заявок нет."
    )
    try:
        await callback.message.edit_text(text, reply_markup=back_kb)
    except Exception:
        await callback.message.answer(text, reply_markup=back_kb)