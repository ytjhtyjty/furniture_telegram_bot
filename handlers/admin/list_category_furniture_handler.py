from html import escape

from aiogram import Router, F, types
from database.crud import CrudCategory
from keyboard.keyboard_builder import make_row_inline_keyboards
from utils.catalog_utils import FURNITURE_TYPE_TITLES
from utils.messages import safe_edit_text

router = Router()

CHUNK_LIMIT = 3800


@router.callback_query(F.data == "list_categories_furniture")
async def list_categories_handler(callback: types.CallbackQuery):
    await callback.answer()
    crud = CrudCategory()
    categories = await crud.get_all_categories()

    back_kb = make_row_inline_keyboards([("⬅️ Назад в админ-панель", "settings_bot")])

    if not categories:
        await safe_edit_text(callback.message, "📭 В базе пока нет ни одной категории.", back_kb)
        return

    header = "📋 <b>Список всех категорий мебели:</b>\n\n"
    lines = []
    for idx, cat in enumerate(categories, start=1):
        type_title = FURNITURE_TYPE_TITLES.get(cat.furniture_type)
        type_part = f" [{escape(type_title)}]" if type_title else ""
        desc = f" — <i>{escape(cat.description)}</i>" if cat.description else ""
        lines.append(f"{idx}. <b>{escape(cat.name)}</b>{type_part}{desc}")

    chunks = []
    current_chunk = header
    for line in lines:
        if len(current_chunk) + len(line) + 1 > CHUNK_LIMIT:
            chunks.append(current_chunk)
            current_chunk = ""
        current_chunk += line + "\n"
    chunks.append(current_chunk)

    for i, chunk in enumerate(chunks):
        is_last = i == len(chunks) - 1
        reply_markup = back_kb if is_last else None
        if i == 0:
            await safe_edit_text(callback.message, chunk, reply_markup)
        else:
            await callback.message.answer(chunk, reply_markup=reply_markup)
