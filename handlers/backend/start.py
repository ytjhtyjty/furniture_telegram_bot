from html import escape
from aiogram import Router, F, types
from aiogram.filters import Command, CommandStart
from aiogram.fsm.context import FSMContext

from database.crud import CrudCategory, CrudFurniture, CrudUser
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

    items.append(("ℹ️ О компании", "about_company"))
    items.append(("🤝 Сотрудничество", "cooperation_company"))

    if user_id in ConfigBot.ADMIN_IDS:
        items.append(("⚙️ Настройки бота", "settings_bot"))

    text = INTRO_TEXT + (CHOOSE_TEXT if categories else EMPTY_TEXT)
    keyboard = make_row_inline_keyboards(items) if items else None
    return text, keyboard


@router.message(CommandStart())
async def cmd_start(message: types.Message, state: FSMContext):
    await state.clear()
    if not message.from_user:
        return

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
    if not callback.from_user:
        return

    text, keyboard = await build_main_menu(callback.from_user.id)

    try:
        await callback.message.delete()
        await callback.message.answer(text, reply_markup=keyboard)
    except Exception:
        try:
            await callback.message.edit_text(text, reply_markup=keyboard)
        except Exception:
            await callback.message.answer(text, reply_markup=keyboard)


@router.callback_query(F.data.startswith("category:"))
async def view_category(callback: types.CallbackQuery):
    await callback.answer()
    try:
        cat_id = int(callback.data.split(":")[1])
    except (ValueError, IndexError):
        return

    await _show_product_page(callback, cat_id=cat_id, product_index=0)


@router.callback_query(F.data.startswith("view_prod:"))
async def navigate_product(callback: types.CallbackQuery):
    await callback.answer()
    parts = callback.data.split(":")
    if len(parts) < 3:
        return
    try:
        cat_id = int(parts[1])
        index = int(parts[2])
    except ValueError:
        return

    await _show_product_page(callback, cat_id=cat_id, product_index=index)


async def _show_product_page(callback: types.CallbackQuery, cat_id: int, product_index: int = 0):
    category = await CrudCategory().get_category_by_id(cat_id)
    if not category:
        back_kb = make_row_inline_keyboards([("⬅️ Назад в меню", "back_to_main")])
        await callback.message.answer("⚠️ Категория не найдена.", reply_markup=back_kb)
        return

    items = await CrudFurniture().get_furniture(category=category.name)
    back_kb = make_row_inline_keyboards([("⬅️ Назад в меню", "back_to_main")])

    if not items:
        text = f"📭 В категории <b>{escape(category.name)}</b> пока нет товаров.\n\nЗагляните позже!"
        try:
            await callback.message.edit_text(text, reply_markup=back_kb)
        except Exception:
            await callback.message.answer(text, reply_markup=back_kb)
        return

    total = len(items)
    if product_index < 0:
        product_index = 0
    elif product_index >= total:
        product_index = total - 1

    product = items[product_index]

    caption = (
        f"🏷 <b>{escape(category.name)}</b> (Товар {product_index + 1} из {total})\n\n"
        f"🌍 <b>Страна/Тип:</b> {escape(product.country_origin or '—')}\n\n"
        f"📝 <b>Описание:</b>\n{escape(product.description or 'Без описания')}"
    )

    buttons = []
    nav = []
    if product_index > 0:
        nav.append(("◀️ Назад", f"view_prod:{cat_id}:{product_index - 1}"))
    if total > 1:
        nav.append((f"{product_index + 1}/{total}", "noop_page"))
    if product_index < total - 1:
        nav.append(("Вперёд ▶️", f"view_prod:{cat_id}:{product_index + 1}"))

    if nav:
        buttons.extend(nav)

    buttons.append(("⬅️ К списку категорий", "back_to_main"))
    keyboard = make_row_inline_keyboards(buttons)

    has_photos = bool(product.photos and len(product.photos) > 0)

    if has_photos:
        first_photo_id = product.photos[0].file_id
        try:
            await callback.message.edit_media(
                media=types.InputMediaPhoto(media=first_photo_id, caption=caption, parse_mode="HTML"),
                reply_markup=keyboard
            )
        except Exception:
            try:
                await callback.message.delete()
            except Exception:
                pass
            await callback.message.answer_photo(photo=first_photo_id, caption=caption, reply_markup=keyboard)
    else:
        try:
            await callback.message.edit_text(caption, reply_markup=keyboard)
        except Exception:
            try:
                await callback.message.delete()
            except Exception:
                pass
            await callback.message.answer(caption, reply_markup=keyboard)


@router.callback_query(F.data == "about_company")
async def about_company_handler(callback: types.CallbackQuery):
    await callback.answer()
    back_kb = make_row_inline_keyboards([("⬅️ Назад", "back_to_main")])
    text = (
        "ℹ️ <b>О компании:</b>\n\n"
        "Мы предлагаем качественную мебель для дома и офиса по доступным ценам.\n"
        "📞 Свяжитесь с нами для консультации и оформления заказа."
    )
    try:
        await callback.message.edit_text(text, reply_markup=back_kb)
    except Exception:
        await callback.message.answer(text, reply_markup=back_kb)


@router.callback_query(F.data == "cooperation_company")
async def cooperation_company_handler(callback: types.CallbackQuery):
    await callback.answer()
    back_kb = make_row_inline_keyboards([("⬅️ Назад", "back_to_main")])
    text = (
        "🤝 <b>Сотрудничество:</b>\n\n"
        "Мы открыты к сотрудничеству с фабриками, дизайнерами и оптовыми клиентами.\n"
        "Напишите нам для обсуждения условий партнёрства."
    )
    try:
        await callback.message.edit_text(text, reply_markup=back_kb)
    except Exception:
        await callback.message.answer(text, reply_markup=back_kb)


@router.message(Command("admin_panel"))
async def admin_panel_denied(message: types.Message):
    await message.answer("⛔ У вас нет доступа к панели администратора.")


@router.callback_query(F.data == "settings_bot")
async def settings_denied(callback: types.CallbackQuery):
    await callback.answer("⛔ У вас нет доступа.", show_alert=True)
