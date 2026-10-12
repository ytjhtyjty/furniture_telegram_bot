from html import escape

from aiogram import Router, F, types
from database.crud import CrudCategory
from keyboard.keyboard_builder import make_row_inline_keyboards

router = Router()

@router.callback_query(F.data == "list_categories_furniture")
async def list_categories_handler(callback: types.CallbackQuery):
    await callback.answer()
    crud = CrudCategory()
    categories = await crud.get_all_categories()

    back_kb = make_row_inline_keyboards([("⬅️ Назад в админ-панель", "settings_bot")])

    if not categories:
        try:
            await callback.message.edit_text("📭 В базе пока нет ни одной категории.", reply_markup=back_kb)
        except Exception:
            await callback.message.answer("📭 В базе пока нет ни одной категории.", reply_markup=back_kb)
        return

    header = "📋 <b>Список всех категорий мебели:</b>\n\n"
    lines = []
    for idx, cat in enumerate(categories, start=1):
        desc = f" — <i>{escape(cat.description)}</i>" if cat.description else ""
        lines.append(f"{idx}. <b>{escape(cat.name)}</b>{desc}")

    chunks = []
    current_chunk = header
    for line in lines:
        if len(current_chunk) + len(line) + 1 > 3800:
            chunks.append(current_chunk)
            current_chunk = line + "\n"
        else:
            current_chunk += line + "\n"
    if current_chunk:
        chunks.append(current_chunk)

    for i, chunk in enumerate(chunks):
        is_last = (i == len(chunks) - 1)
        reply_markup = back_kb if is_last else None
        if i == 0:
            try:
                await callback.message.edit_text(chunk, reply_markup=reply_markup)
            except Exception:
                await callback.message.answer(chunk, reply_markup=reply_markup)
        else:
            await callback.message.answer(chunk, reply_markup=reply_markup)