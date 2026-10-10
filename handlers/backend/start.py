from aiogram import Router, F, types
from aiogram.filters import Command, CommandStart
from aiogram.fsm.context import FSMContext

from database.crud import CrudCategory, CrudUser
from keyboard.keyboard_builder import make_row_inline_keyboards
from settings.config import ConfigBot


router = Router()


INTRO_TEXT = (
    "🌟 <b>Добро пожаловать в наш мебельный бот!</b> 🌟\n\n"
    "🛋 Здесь вы найдёте стильную и качественную мебель "
    "для любого интерьера.\n\n"
)
CHOOSE_TEXT = "👇 <b>Выберите категорию из меню ниже:</b>"
EMPTY_TEXT = "📭 Каталог пока пуст, загляните позже."



async def build_main_menu(user_id: int) -> tuple[str, types.InlineKeyboardMarkup | None]:
    categories = await CrudCategory().get_all_categories()
    items = [(cat.name, f"category:{cat.id}") for cat in categories]

    if user_id in ConfigBot.ADMIN_IDS:
        items.append(("⚙️ Настройки бота", "settings_bot"))

    text = INTRO_TEXT + (CHOOSE_TEXT if categories else EMPTY_TEXT)
    keyboard = make_row_inline_keyboards(items) if items else None
    return text, keyboard



@router.message(CommandStart())
async def cmd_start(message: types.Message, state: FSMContext):
    await state.clear()

    await CrudUser().get_or_create_user(
        telegram_id=message.from_user.id,
        username=message.from_user.username,
        firstname=message.from_user.first_name,
        lastname=message.from_user.last_name,
    )

    text, keyboard = await build_main_menu(message.from_user.id)
    await message.answer(text, reply_markup=keyboard)



@router.callback_query(F.data == "back_to_main")
async def back_to_main(callback: types.CallbackQuery, state: FSMContext):
    await state.clear()
    await callback.answer()
    text, keyboard = await build_main_menu(callback.from_user.id)
    try:
        await callback.message.edit_text(text, reply_markup=keyboard)
    except Exception:
        await callback.message.answer(text, reply_markup=keyboard)


@router.message(Command("admin_panel"))
async def admin_panel_denied(message: types.Message):
    await message.answer("⛔ У вас нет доступа к панели администратора.")


@router.callback_query(F.data == "settings_bot")
async def settings_denied(callback: types.CallbackQuery):
    await callback.answer("⛔ У вас нет доступа.", show_alert=True)
