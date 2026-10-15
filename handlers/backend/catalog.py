import logging
from contextlib import suppress
from html import escape

from aiogram import F, Router
from aiogram.exceptions import TelegramBadRequest
from aiogram.fsm.context import FSMContext
from aiogram.types import (
    CallbackQuery,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    InputMediaPhoto,
    Message,
)

from database.crud import CrudCategory, CrudFurniture
from database.models import Category, Furniture
from keyboard.button_template import (
    country_of_origin_kb,
    kitchen_subcategory_inline_kb,
)
from utils.catalog_utils import (
    COUNTRY_BY_CB,
    KITCHEN_COUNTRY,
    KITCHEN_TYPE_BY_CB,
    MODE_COUNTRY,
    MODE_KITCHEN,
    get_category_mode,
    split_kitchen_prefix,
)
from utils.messages import contacts_block, safe_edit_text

logger = logging.getLogger(__name__)
router = Router()

CAPTION_LIMIT = 1024
NO_ITEMS_TEXT = "В этой категории пока нет товаров"
BACK_TO_CATEGORIES = "back_to_categories"


def _country_line(country: str | None) -> str:
    if country == "Россия":
        return "🇷🇺 Страна производства: Россия"
    if country == "Турция":
        return "🇹🇷 Страна производства: Турция"
    if country:
        return f"🌍 Страна производства: {escape(country)}"
    return ""


def _choices_kb(options: list[tuple[str, str]], back_cb: str) -> InlineKeyboardMarkup:
    rows = [
        [InlineKeyboardButton(text=text, callback_data=cb)]
        for text, cb in options
        if cb != "back_to_main"
    ]
    rows.append([InlineKeyboardButton(text="⬅️ Назад", callback_data=back_cb)])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def _back_kb(back_cb: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[[InlineKeyboardButton(text="⬅️ Назад", callback_data=back_cb)]]
    )


def _product_keyboard(
    product_idx: int,
    total_products: int,
    has_multiple_photos: bool,
    back_cb: str,
) -> InlineKeyboardMarkup:
    rows = []

    if total_products > 1:
        prev_cb = f"product_nav:{product_idx - 1}" if product_idx > 0 else "noop"
        next_cb = (
            f"product_nav:{product_idx + 1}"
            if product_idx < total_products - 1
            else "noop"
        )
        rows.append([
            InlineKeyboardButton(text="◀️", callback_data=prev_cb),
            InlineKeyboardButton(
                text=f"{product_idx + 1}/{total_products}", callback_data="noop"
            ),
            InlineKeyboardButton(text="▶️", callback_data=next_cb),
        ])

    if has_multiple_photos:
        rows.append([
            InlineKeyboardButton(
                text="📷 Посмотреть подробнее",
                callback_data=f"photo_nav:{product_idx}:0",
            )
        ])

    rows.append([InlineKeyboardButton(text="⬅️ Назад", callback_data=back_cb)])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def _photo_keyboard(
    product_idx: int,
    photo_idx: int,
    total_photos: int,
) -> InlineKeyboardMarkup:
    prev_cb = (
        f"photo_nav:{product_idx}:{photo_idx - 1}" if photo_idx > 0 else "noop"
    )
    next_cb = (
        f"photo_nav:{product_idx}:{photo_idx + 1}"
        if photo_idx < total_photos - 1
        else "noop"
    )
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="◀️", callback_data=prev_cb),
            InlineKeyboardButton(
                text=f"📷 {photo_idx + 1}/{total_photos}", callback_data="noop"
            ),
            InlineKeyboardButton(text="▶️", callback_data=next_cb),
        ],
        [
            InlineKeyboardButton(
                text="⬅️ Назад к товару",
                callback_data=f"back_to_product:{product_idx}",
            )
        ],
    ])


def _build_caption(category: Category, item: Furniture, footer: str) -> str:
    kitchen_type, description = split_kitchen_prefix(item.description)

    head = f"🛋 <b>{escape(category.name)}</b>"

    info = []
    if kitchen_type:
        info.append(f"📐 Тип кухни: {escape(kitchen_type)}")
    country_part = _country_line(item.country_origin)
    if country_part:
        info.append(country_part)
    if item.created_at:
        info.append(f"📅 Дата добавления: {item.created_at.strftime('%d.%m.%Y')}")

    tail_parts = ["\n".join(info), contacts_block(), footer]
    tail = "\n\n" + "\n\n".join(part for part in tail_parts if part)

    description = description.strip() or "Без описания"
    room = CAPTION_LIMIT - len(head) - len(tail) - 2
    if len(description) > room:
        description = description[: max(0, room - 1)].rstrip() + "…"

    return f"{head}\n\n{escape(description)}{tail}"


def _has_message(callback: CallbackQuery) -> bool:
    return isinstance(callback.message, Message)


async def _find_category(category_id: int | None) -> Category | None:
    if category_id is None:
        return None
    return await CrudCategory().get_category_by_id(category_id)


async def _show(callback: CallbackQuery, text: str, kb: InlineKeyboardMarkup) -> None:
    await safe_edit_text(callback.message, text, kb)


async def _send_photo_card(
    callback: CallbackQuery,
    file_id: str | None,
    caption: str,
    kb: InlineKeyboardMarkup,
) -> None:
    message = callback.message
    try:
        if file_id:
            await message.edit_media(
                media=InputMediaPhoto(media=file_id, caption=caption), reply_markup=kb
            )
        else:
            await message.edit_text(text=caption, reply_markup=kb)
        return
    except TelegramBadRequest as e:
        if "message is not modified" in str(e):
            return

    if file_id:
        await message.answer_photo(photo=file_id, caption=caption, reply_markup=kb)
    else:
        await message.answer(caption, reply_markup=kb)
    with suppress(TelegramBadRequest):
        await message.delete()


async def _show_categories(callback: CallbackQuery) -> None:
    categories = await CrudCategory().get_all_categories()
    rows = [
        [InlineKeyboardButton(text=c.name, callback_data=f"category:{c.id}")]
        for c in categories
    ]
    rows.append([InlineKeyboardButton(text="⬅️ Назад", callback_data="back_to_main")])
    await _show(
        callback,
        "Выберите категорию:",
        InlineKeyboardMarkup(inline_keyboard=rows),
    )


async def _get_items(category: Category, country: str | None, kitchen_type: str | None) -> list[Furniture]:
    items = await CrudFurniture().get_furniture(category.name, country)
    if kitchen_type:
        items = [
            i for i in items
            if split_kitchen_prefix(i.description)[0] == kitchen_type
        ]
    return items


async def _render_product(
    callback: CallbackQuery,
    category: Category,
    items: list[Furniture],
    product_idx: int,
    back_cb: str,
) -> None:
    """Карточка товара: одно фото + описание + навигация по товарам."""
    if not items:
        await _show(callback, NO_ITEMS_TEXT, _back_kb(back_cb))
        return

    product_idx = max(0, min(product_idx, len(items) - 1))
    item = items[product_idx]
    total = len(items)

    caption = _build_caption(
        category, item, f"📦 Показано {product_idx + 1} из {total} товаров в категории"
    )

    file_ids = list(dict.fromkeys(p.file_id for p in item.photos))
    kb = _product_keyboard(product_idx, total, len(file_ids) > 1, back_cb)
    await _send_photo_card(callback, file_ids[0] if file_ids else None, caption, kb)


async def _render_photo(
    callback: CallbackQuery,
    category: Category,
    items: list[Furniture],
    product_idx: int,
    photo_idx: int,
    back_cb: str,
) -> None:
    if not items:
        await _show(callback, NO_ITEMS_TEXT, _back_kb(back_cb))
        return

    product_idx = max(0, min(product_idx, len(items) - 1))
    item = items[product_idx]
    file_ids = list(dict.fromkeys(p.file_id for p in item.photos))
    total_photos = len(file_ids)

    if total_photos == 0:
        await _render_product(callback, category, items, product_idx, back_cb)
        return

    photo_idx = max(0, min(photo_idx, total_photos - 1))
    caption = _build_caption(category, item, f"📷 Фото {photo_idx + 1} из {total_photos}")
    kb = _photo_keyboard(product_idx, photo_idx, total_photos)
    await _send_photo_card(callback, file_ids[photo_idx], caption, kb)


async def _show_products(
    callback: CallbackQuery,
    category: Category,
    country: str | None,
    kitchen_type: str | None,
    back_cb: str,
) -> None:
    items = await _get_items(category, country, kitchen_type)
    await _render_product(callback, category, items, 0, back_cb)


async def _open_category(callback: CallbackQuery, state: FSMContext, category: Category) -> None:
    await state.set_state(None)
    await state.update_data(
        catalog_category_id=category.id,
        catalog_country=None,
        catalog_kitchen_type=None,
        catalog_back_cb=BACK_TO_CATEGORIES,
    )

    mode = get_category_mode(category)
    if mode == MODE_KITCHEN:
        await _show(
            callback,
            "📐 Выберите тип кухни:",
            _choices_kb(kitchen_subcategory_inline_kb, BACK_TO_CATEGORIES),
        )
    elif mode == MODE_COUNTRY:
        await _show(
            callback,
            "Отлично! Теперь выберите страну производства:",
            _choices_kb(country_of_origin_kb, BACK_TO_CATEGORIES),
        )
    else:
        await _show_products(callback, category, None, None, BACK_TO_CATEGORIES)


async def _browsing_context(callback: CallbackQuery, state: FSMContext):
    data = await state.get_data()
    category = await _find_category(data.get("catalog_category_id"))
    if category is None:
        await state.clear()
        await _show_categories(callback)
        return None
    return (
        category,
        data.get("catalog_country"),
        data.get("catalog_kitchen_type"),
        data.get("catalog_back_cb") or BACK_TO_CATEGORIES,
    )


@router.callback_query(F.data.startswith("category:"))
async def open_category(callback: CallbackQuery, state: FSMContext):
    await callback.answer()
    if not _has_message(callback):
        return
    try:
        category_id = int(callback.data.split(":", 1)[1])
    except ValueError:
        return

    category = await _find_category(category_id)
    if category is None:
        await _show_categories(callback)
        return

    await _open_category(callback, state, category)


@router.callback_query(F.data.in_(frozenset(KITCHEN_TYPE_BY_CB)))
async def choose_kitchen_type(callback: CallbackQuery, state: FSMContext):
    await callback.answer()
    if not _has_message(callback):
        return

    context = await _browsing_context(callback, state)
    if context is None:
        return
    category = context[0]

    kitchen_type = KITCHEN_TYPE_BY_CB[callback.data]
    back_cb = f"back_to_category:{category.id}"

    await state.update_data(
        catalog_country=KITCHEN_COUNTRY,
        catalog_kitchen_type=kitchen_type,
        catalog_back_cb=back_cb,
    )
    await _show_products(callback, category, KITCHEN_COUNTRY, kitchen_type, back_cb)


@router.callback_query(F.data.in_(frozenset(COUNTRY_BY_CB)))
async def choose_country(callback: CallbackQuery, state: FSMContext):
    await callback.answer()
    if not _has_message(callback):
        return

    context = await _browsing_context(callback, state)
    if context is None:
        return
    category = context[0]

    country = COUNTRY_BY_CB[callback.data]
    back_cb = f"back_to_category:{category.id}"

    await state.update_data(
        catalog_country=country,
        catalog_kitchen_type=None,
        catalog_back_cb=back_cb,
    )
    await _show_products(callback, category, country, None, back_cb)


@router.callback_query(F.data.startswith("product_nav:"))
async def navigate_products(callback: CallbackQuery, state: FSMContext):
    await callback.answer()
    if not _has_message(callback):
        return
    try:
        idx = int(callback.data.split(":", 1)[1])
    except ValueError:
        return

    context = await _browsing_context(callback, state)
    if context is None:
        return
    category, country, kitchen_type, back_cb = context

    items = await _get_items(category, country, kitchen_type)
    await _render_product(callback, category, items, idx, back_cb)


@router.callback_query(F.data.startswith("photo_nav:"))
async def navigate_photos(callback: CallbackQuery, state: FSMContext):
    await callback.answer()
    if not _has_message(callback):
        return
    parts = callback.data.split(":")
    if len(parts) != 3:
        return
    try:
        product_idx = int(parts[1])
        photo_idx = int(parts[2])
    except ValueError:
        return

    context = await _browsing_context(callback, state)
    if context is None:
        return
    category, country, kitchen_type, back_cb = context

    items = await _get_items(category, country, kitchen_type)
    await _render_photo(callback, category, items, product_idx, photo_idx, back_cb)


@router.callback_query(F.data.startswith("back_to_product:"))
async def back_to_product(callback: CallbackQuery, state: FSMContext):
    await callback.answer()
    if not _has_message(callback):
        return
    try:
        product_idx = int(callback.data.split(":", 1)[1])
    except ValueError:
        return

    context = await _browsing_context(callback, state)
    if context is None:
        return
    category, country, kitchen_type, back_cb = context

    items = await _get_items(category, country, kitchen_type)
    await _render_product(callback, category, items, product_idx, back_cb)


@router.callback_query(F.data == "noop")
async def noop(callback: CallbackQuery):
    await callback.answer()


@router.callback_query(F.data.startswith("back_to_category:"))
async def back_to_category(callback: CallbackQuery, state: FSMContext):
    await callback.answer()
    if not _has_message(callback):
        return
    try:
        category_id = int(callback.data.split(":", 1)[1])
    except ValueError:
        return

    category = await _find_category(category_id)
    if category is None:
        await _show_categories(callback)
        return

    await _open_category(callback, state, category)


@router.callback_query(F.data == BACK_TO_CATEGORIES)
async def back_to_categories(callback: CallbackQuery):
    await callback.answer()
    if not _has_message(callback):
        return
    await _show_categories(callback)


@router.callback_query()
async def stale_callback(callback: CallbackQuery):
    logger.info("Необработанный callback %r от %s", callback.data, callback.from_user.id)
    kb = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="🏠 Главное меню", callback_data="back_to_main")]
        ]
    )
    await callback.answer("Это меню устарело.", show_alert=False)
    await safe_edit_text(
        callback.message,
        "⚠️ Это меню устарело. Нажмите кнопку ниже или /start.",
        kb,
    )