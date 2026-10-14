import asyncio
from collections import defaultdict
from html import escape

from aiogram import Router, F, types
from aiogram.fsm.context import FSMContext
from states.states import NewFurnitureStates
from keyboard.keyboard_builder import make_row_keyboards, make_row_inline_keyboards
from keyboard.button_template import (
    country_of_origin_kb,
    finish_furniture_kb,
    furniture_cancel_kb,
    kitchen_subcategory_inline_kb,
)
from database.crud import CrudCategory, CrudFurniture
from utils.catalog_utils import (
    COUNTRY_BY_CB,
    FURNITURE_DESCRIPTION_MAX,
    KITCHEN_COUNTRY,
    KITCHEN_TYPE_BY_CB,
    MAX_PHOTOS,
    MODE_KITCHEN,
    get_category_mode,
)
from utils.filters import NotCommand
from utils.messages import safe_edit_text
from .main_admin import show_admin_panel

router = Router()

CANCEL_TEXT = "❌ Отменить"

_user_locks: defaultdict[int, asyncio.Lock] = defaultdict(asyncio.Lock)


def _choice_kb(template: list[tuple[str, str]]) -> types.InlineKeyboardMarkup:
    """Варианты из шаблона без клиентской кнопки «Назад» + кнопка «Отменить»."""
    options = [(text, cb) for text, cb in template if cb != "back_to_main"]
    return make_row_inline_keyboards(options + furniture_cancel_kb)


@router.callback_query(F.data == "new_furniture")
async def start_add_furniture(callback: types.CallbackQuery, state: FSMContext):
    await callback.answer()
    await state.clear()

    categories_from_db = await CrudCategory().get_all_categories()
    if not categories_from_db:
        await callback.message.answer("⚠️ В базе данных пока нет категорий! Сначала создайте категорию.")
        await show_admin_panel(callback.message, state, admin=callback.from_user)
        return

    category_modes = {cat.name: get_category_mode(cat) for cat in categories_from_db}
    await state.update_data(category_modes=category_modes)
    await state.set_state(NewFurnitureStates.category)

    await callback.message.answer(
        "🪑 <b>Добавление новой мебели</b>\n\n"
        "<b>Шаг 1:</b> Выберите категорию для мебели из кнопок ниже:",
        reply_markup=make_row_keyboards(list(category_modes) + [CANCEL_TEXT])
    )


@router.message(NewFurnitureStates.category, NotCommand())
async def process_furniture_category(message: types.Message, state: FSMContext):
    category_name = (message.text or "").strip()

    if category_name == CANCEL_TEXT:
        await state.clear()
        await message.answer("🚫 Добавление мебели отменено.", reply_markup=types.ReplyKeyboardRemove())
        await show_admin_panel(message, state)
        return

    data = await state.get_data()
    category_modes = data.get("category_modes", {})
    if category_name not in category_modes:
        await message.answer("⚠️ Такой категории нет. Выберите категорию кнопкой из списка ниже.")
        return

    await state.update_data(category=category_name)
    await message.answer(
        f"✅ Категория: <b>{escape(category_name)}</b>",
        reply_markup=types.ReplyKeyboardRemove()
    )

    if category_modes[category_name] == MODE_KITCHEN:
        await state.update_data(country=KITCHEN_COUNTRY)
        await state.set_state(NewFurnitureStates.kitchen_type)
        await message.answer(
            "<b>Шаг 2:</b> 📐 Выберите тип кухонного гарнитура:",
            reply_markup=_choice_kb(kitchen_subcategory_inline_kb)
        )
    else:
        await state.set_state(NewFurnitureStates.country)
        await message.answer(
            "<b>Шаг 2:</b> 🌍 Выберите страну производства:",
            reply_markup=_choice_kb(country_of_origin_kb)
        )


async def _ask_description(message: types.Message, state: FSMContext) -> None:
    await state.set_state(NewFurnitureStates.description)
    await message.edit_text(
        "<b>Шаг 3:</b> Отправьте подробное описание товара в одном сообщении:\n"
        "• Название\n"
        "• Габариты (длина x ширина x высота)\n"
        "• Материал каркаса и обивки\n"
        "• Стоимость\n\n"
        f"<i>Не более {FURNITURE_DESCRIPTION_MAX} символов.</i>",
        reply_markup=make_row_inline_keyboards(furniture_cancel_kb)
    )


@router.callback_query(NewFurnitureStates.kitchen_type, F.data.in_(set(KITCHEN_TYPE_BY_CB)))
async def process_kitchen_type(callback: types.CallbackQuery, state: FSMContext):
    await callback.answer()
    await state.update_data(kitchen_type=KITCHEN_TYPE_BY_CB[callback.data])
    await _ask_description(callback.message, state)


@router.callback_query(NewFurnitureStates.country, F.data.in_(set(COUNTRY_BY_CB)))
async def process_country(callback: types.CallbackQuery, state: FSMContext):
    await callback.answer()
    await state.update_data(country=COUNTRY_BY_CB[callback.data])
    await _ask_description(callback.message, state)


@router.message(NewFurnitureStates.kitchen_type, NotCommand())
@router.message(NewFurnitureStates.country, NotCommand())
async def process_choice_as_text(message: types.Message):
    await message.answer("⚠️ Выберите вариант кнопкой под сообщением выше или нажмите «Отменить».")


@router.message(NewFurnitureStates.description, NotCommand())
async def process_furniture_description(message: types.Message, state: FSMContext):
    description = (message.text or "").strip()
    if not description:
        await message.answer(
            "⚠️ Описание не может быть пустым. Отправьте описание текстом:",
            reply_markup=make_row_inline_keyboards(furniture_cancel_kb)
        )
        return

    if len(description) > FURNITURE_DESCRIPTION_MAX:
        await message.answer(
            f"⚠️ Описание слишком длинное ({len(description)} символов, максимум "
            f"{FURNITURE_DESCRIPTION_MAX}). Сократите и отправьте ещё раз:",
            reply_markup=make_row_inline_keyboards(furniture_cancel_kb)
        )
        return

    await state.update_data(description=description)
    await init_photo_upload(message, state)


async def init_photo_upload(message: types.Message, state: FSMContext):
    await state.set_state(NewFurnitureStates.photos)
    await state.update_data(photos=[], photo_limit_warned=False)  # Пустой список для file_id

    await message.answer(
        "📸 <b>Шаг 4: Загрузка фотографий</b>\n\n"
        f"Отправьте от 1 до {MAX_PHOTOS} фотографий мебели.\n"
        "Когда закончите отправку, нажмите кнопку <b>«Завершить добавление»</b>.",
        reply_markup=make_row_inline_keyboards(finish_furniture_kb + furniture_cancel_kb)
    )


@router.message(NewFurnitureStates.photos, F.photo)
async def process_incoming_photo(message: types.Message, state: FSMContext):
    async with _user_locks[message.from_user.id]:
        data = await state.get_data()
        photos = data.get("photos", [])

        if len(photos) >= MAX_PHOTOS:
            if not data.get("photo_limit_warned"):
                await state.update_data(photo_limit_warned=True)
                reply = (
                    f"⚠️ Достигнут лимит (максимум {MAX_PHOTOS} фотографий). "
                    "Лишние фото не сохранены. Нажмите «Завершить добавление»."
                )
            else:
                return
        else:
            best_photo_file_id = message.photo[-1].file_id
            if best_photo_file_id in photos:
                return
            photos.append(best_photo_file_id)
            await state.update_data(photos=photos)
            reply = f"📸 Фото принято ({len(photos)} из {MAX_PHOTOS}). Отправьте еще или завершите."

    await message.answer(
        reply,
        reply_markup=make_row_inline_keyboards(finish_furniture_kb + furniture_cancel_kb)
    )


@router.message(NewFurnitureStates.photos, NotCommand())
async def process_not_photo(message: types.Message):
    await message.answer(
        "⚠️ На этом шаге нужно отправить фотографию (как фото, не файлом) "
        "или нажать «Завершить добавление».",
        reply_markup=make_row_inline_keyboards(finish_furniture_kb + furniture_cancel_kb)
    )


@router.callback_query(F.data == "finish_furniture_creation")
async def finish_furniture_save(callback: types.CallbackQuery, state: FSMContext):
    await callback.answer()

    async with _user_locks[callback.from_user.id]:
        data = await state.get_data()

        if not data or "category" not in data or "description" not in data:
            await callback.message.answer("⚠️ Данные устарели или не найдены. Начните добавление мебели сначала.")
            await state.clear()
            return

        photos = data.get("photos", [])
        if not photos:
            await callback.message.answer("⚠️ Нельзя создать товар без фотографий! Отправьте хотя бы 1 фото.")
            return

        await state.clear()

    desc = data["description"]
    kitchen_type = data.get("kitchen_type")
    if kitchen_type:
        desc = f"[{kitchen_type}] {desc}"

    furniture = await CrudFurniture().create_furniture(
        description=desc,
        category=data["category"],
        country=data.get("country", KITCHEN_COUNTRY),
        photos=photos
    )

    if not furniture:
        await callback.message.answer("❌ Ошибка базы данных при сохранении мебели.")
        await show_admin_panel(callback.message, state, admin=callback.from_user)
        return

    await callback.message.answer(
        "🎉 <b>Мебель успешно добавлена в каталог!</b>\n\n"
        f"📦 <b>Категория:</b> {escape(data['category'])}\n"
        f"🌍 <b>Страна/Тип:</b> {escape(kitchen_type or data.get('country') or '—')}\n"
        f"🖼 <b>Количество фото:</b> {len(photos)} шт.\n\n"
        f"📝 <b>Описание:</b>\n{escape(desc)}"
    )

    await show_admin_panel(callback.message, state, admin=callback.from_user)


@router.callback_query(F.data == "cancel_furniture")
async def cancel_furniture_handler(callback: types.CallbackQuery, state: FSMContext):
    already_cancelled = await state.get_state() is None
    await callback.answer()
    if already_cancelled:
        return
    await state.clear()
    await safe_edit_text(callback.message, "🚫 Добавление мебели отменено.")
    await show_admin_panel(callback.message, state, admin=callback.from_user)
