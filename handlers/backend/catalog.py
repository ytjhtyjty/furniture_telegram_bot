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
NO_FILTER = "-"


def _country_line(country: str | None) -> str:
    if country == "Россия":
        return "🇷🇺 Страна производства: Россия"
    if country == "Турция":
        return "🇹🇷 Страна производства: Турция"
    if country:
        return f"🌍 Страна производства: {escape(country)}"
    return ""


def _view(category_id: int, filter_cb: str) -> str:
    return f"{category_id}:{filter_cb}"


def _back_cb_for(category_id: int, filter_cb: str) -> str:
    return BACK_TO_CATEGORIES if filter_cb == NO_FILTER else f"back_to_category:{category_id}"


def _choices_kb(options: list[tuple[str, str]], category_id: int, back_cb: str) -> InlineKeyboardMarkup:
    rows = [
        [InlineKeyboardButton(text=text, callback_data=f"catalog_filter:{_view(category_id, cb)}")]
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
    view: str,
    product_idx: int,
    total_products: int,
    has_multiple_photos: bool,
    back_cb: str,
) -> InlineKeyboardMarkup:
    rows = []

    if total_products > 1:
        prev_cb = f"product_nav:{view}:{product_idx - 1}" if product_idx > 0 else "noop"
        next_cb = (
            f"product_nav:{view}:{product_idx + 1}"
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
                callback_data=f"photo_nav:{view}:{product_idx}:0",
            )
        ])

    rows.append([InlineKeyboardButton(text="⬅️ Назад", callback_data=back_cb)])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def _photo_keyboard(
    view: str,
    product_idx: int,
    photo_idx: int,
    total_photos: int,
) -> InlineKeyboardMarkup:
    prev_cb = (
        f"photo_nav:{view}:{product_idx}:{photo_idx - 1}" if photo_idx > 0 else "noop"
    )
    next_cb = (
        f"photo_nav:{view}:{product_idx}:{photo_idx + 1}"
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
                callback_data=f"back_to_product:{view}:{product_idx}",
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
    filter_cb: str,
    items: list[Furniture],
    product_idx: int,
) -> None:
    back_cb = _back_cb_for(category.id, filter_cb)
    if not items:
        await _show(callback, NO_ITEMS_TEXT, _back_kb(back_cb))
        return

    product_idx = max(0, min(product_idx, len(items) - 1))
    item = items[product_idx]
    total = len(items)

    caption = _build_caption(
        category, item, f"📦 Показано {product_idx + 1} из {total} товаров в категории"
    )

    file_ids = [p.file_id for p in item.photos]
    kb = _product_keyboard(
        _view(category.id, filter_cb), product_idx, total, len(file_ids) > 1, back_cb
    )
    await _send_photo_card(callback, file_ids[0] if file_ids else None, caption, kb)


async def _render_photo(
    callback: CallbackQuery,
    category: Category,
    filter_cb: str,
    items: list[Furniture],
    product_idx: int,
    photo_idx: int,
) -> None:
    if not items:
        await _show(callback, NO_ITEMS_TEXT, _back_kb(_back_cb_for(category.id, filter_cb)))
        return

    product_idx = max(0, min(product_idx, len(items) - 1))
    item = items[product_idx]
    file_ids = [p.file_id for p in item.photos]
    total_photos = len(file_ids)

    if total_photos == 0:
        await _render_product(callback, category, filter_cb, items, product_idx)
        return

    photo_idx = max(0, min(photo_idx, total_photos - 1))
    caption = _build_caption(category, item, f"📷 Фото {photo_idx + 1} из {total_photos}")
    kb = _photo_keyboard(_view(category.id, filter_cb), product_idx, photo_idx, total_photos)
    await _send_photo_card(callback, file_ids[photo_idx], caption, kb)


async def _open_category(callback: CallbackQuery, state: FSMContext, category: Category) -> None:
    await state.set_state(None)

    mode = get_category_mode(category)
    if mode == MODE_KITCHEN:
        await _show(
            callback,
            "📐 Выберите тип кухни:",
            _choices_kb(kitchen_subcategory_inline_kb, category.id, BACK_TO_CATEGORIES),
        )
    elif mode == MODE_COUNTRY:
        await _show(
            callback,
            "Отлично! Теперь выберите страну производства:",
            _choices_kb(country_of_origin_kb, category.id, BACK_TO_CATEGORIES),
        )
    else:
        items = await _get_items(category, None, None)
        await _render_product(callback, category, NO_FILTER, items, 0)


async def _resolve_view(
    callback: CallbackQuery,
    category_id: str,
    filter_cb: str,
) -> tuple[Category, str, list[Furniture]] | None:
    country, kitchen_type = None, None
    if filter_cb in COUNTRY_BY_CB:
        country = COUNTRY_BY_CB[filter_cb]
    elif filter_cb in KITCHEN_TYPE_BY_CB:
        country, kitchen_type = KITCHEN_COUNTRY, KITCHEN_TYPE_BY_CB[filter_cb]
    elif filter_cb != NO_FILTER:
        return None

    try:
        category = await _find_category(int(category_id))
    except ValueError:
        category = None
    if category is None:
        await _show_categories(callback)
        return None

    items = await _get_items(category, country, kitchen_type)
    return category, filter_cb, items


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


@router.callback_query(F.data.startswith("catalog_filter:"))
async def choose_filter(callback: CallbackQuery):
    await callback.answer()
    if not _has_message(callback):
        return
    parts = callback.data.split(":")
    if len(parts) != 3:
        return

    resolved = await _resolve_view(callback, parts[1], parts[2])
    if resolved is None:
        return
    category, filter_cb, items = resolved
    await _render_product(callback, category, filter_cb, items, 0)


@router.callback_query(F.data.startswith("product_nav:"))
async def navigate_products(callback: CallbackQuery):
    await callback.answer()
    if not _has_message(callback):
        return
    parts = callback.data.split(":")
    if len(parts) != 4:
        return
    try:
        idx = int(parts[3])
    except ValueError:
        return

    resolved = await _resolve_view(callback, parts[1], parts[2])
    if resolved is None:
        return
    category, filter_cb, items = resolved
    await _render_product(callback, category, filter_cb, items, idx)


@router.callback_query(F.data.startswith("photo_nav:"))
async def navigate_photos(callback: CallbackQuery):
    await callback.answer()
    if not _has_message(callback):
        return
    parts = callback.data.split(":")
    if len(parts) != 5:
        return
    try:
        product_idx = int(parts[3])
        photo_idx = int(parts[4])
    except ValueError:
        return

    resolved = await _resolve_view(callback, parts[1], parts[2])
    if resolved is None:
        return
    category, filter_cb, items = resolved
    await _render_photo(callback, category, filter_cb, items, product_idx, photo_idx)


@router.callback_query(F.data.startswith("back_to_product:"))
async def back_to_product(callback: CallbackQuery):
    await callback.answer()
    if not _has_message(callback):
        return
    parts = callback.data.split(":")
    if len(parts) != 4:
        return
    try:
        product_idx = int(parts[3])
    except ValueError:
        return

    resolved = await _resolve_view(callback, parts[1], parts[2])
    if resolved is None:
        return
    category, filter_cb, items = resolved
    await _render_product(callback, category, filter_cb, items, product_idx)


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
    await callback.answer("Это меню устарело. Нажмите /start, чтобы открыть актуальное.", show_alert=True)
