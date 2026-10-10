from aiogram import Router, F, types
from aiogram.filters import CommandStart
from aiogram.fsm.context import FSMContext

from database.crud import CrudCategory
from keyboard.keyboard_builder import make_row_inline_keyboards
from settings.config import ConfigBot

router = Router()

WELCOME_TEXT = (
    "🌟 <b>Добро пожаловать в наш мебельный бот!</b> 🌟\n\n"
    "🛋 Здесь вы найдёте стильную и качественную мебель "
    "для любого интерьера.\n\n"
    "👇 <b>Выберите категорию из меню ниже:</b>"
)


async def build_main_menu(user_id: int) -> types.InlineKeyboardMarkup:
    categories = await CrudCategory().get_all_categories()
    items = [(cat.name, f"category:{cat.id}") for cat in categories]
    if user_id in ConfigBot.ADMIN_IDS:
        items.append(("⚙️ Настройки бота", "settings_bot"))
    return make_row_inline_keyboards(items)


@router.message(CommandStart())
async def cmd_start(message: types.Message, state: FSMContext):
    await state.clear()
    keyboard = await build_main_menu(message.from_user.id)
    await message.answer(WELCOME_TEXT, reply_markup=keyboard)


@router.callback_query(F.data == "back_to_main")
async def back_to_main(callback: types.CallbackQuery, state: FSMContext):
    await state.clear()
    await callback.answer()
    keyboard = await build_main_menu(callback.from_user.id)
    try:
        await callback.message.edit_text(WELCOME_TEXT, reply_markup=keyboard)
    except Exception:
        await callback.message.answer(WELCOME_TEXT, reply_markup=keyboard)
