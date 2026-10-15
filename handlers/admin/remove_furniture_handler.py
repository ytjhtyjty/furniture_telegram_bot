from html import escape
from aiogram import Router, F, types
from aiogram.fsm.context import FSMContext

from database.crud import CrudFurniture
from keyboard.keyboard_builder import make_row_inline_keyboards
from states.states import RemoveFurnitureStates
from utils.messages import safe_edit_text

router = Router()

PAGE_SIZE = 8
SNIPPET_LEN = 30


def _snippet(description: str | None) -> str:
    lines = (description or "").strip().splitlines()
    text = lines[0].strip() if lines else "без описания"
    return text if len(text) <= SNIPPET_LEN else text[:SNIPPET_LEN].rstrip() + "…"


def _parse_id_and_page(data: str) -> tuple[int, int] | None:
    parts = data.split(":")
    if len(parts) != 3:
        return None
    try:
        return int(parts[1]), int(parts[2])
    except ValueError:
        return None


async def _render_furniture_list_page(callback: types.CallbackQuery, page: int = 0):
    crud = CrudFurniture()
    page = max(0, page)
    items, total = await crud.get_furniture_paginated(offset=page * PAGE_SIZE, limit=PAGE_SIZE)

    if total == 0:
        back_kb = make_row_inline_keyboards([("⬅️ В админ-панель", "settings_bot")])
        await safe_edit_text(callback.message, "📭 Каталог пуст. Нет товаров для удаления.", back_kb)
        return

    total_pages = max(1, (total + PAGE_SIZE - 1) // PAGE_SIZE)
    if page >= total_pages:
        page = total_pages - 1
        items, _ = await crud.get_furniture_paginated(offset=page * PAGE_SIZE, limit=PAGE_SIZE)

    buttons = [
        (f"🗑 #{item.id} {_snippet(item.description)}", f"ask_delete:{item.id}:{page}")
        for item in items
    ]

    nav_row = []
    if page > 0:
        nav_row.append(("◀️", f"remove_furniture_page:{page - 1}"))
    if total_pages > 1:
        nav_row.append((f"{page + 1}/{total_pages}", "noop_page"))
    if page < total_pages - 1:
        nav_row.append(("▶️", f"remove_furniture_page:{page + 1}"))
    if nav_row:
        buttons.extend(nav_row)

    buttons.append(("⬅️ В админ-панель", "settings_bot"))

    text = (
        f"🗑 <b>Удаление мебели</b> (Всего товаров: {total})\n\n"
        "Выберите товар для подтверждения удаления:"
    )
    await safe_edit_text(callback.message, text, make_row_inline_keyboards(buttons))


@router.callback_query(F.data == "remove_furniture")
async def show_furniture_to_remove(callback: types.CallbackQuery, state: FSMContext):
    await callback.answer()
    await state.clear()
    await state.set_state(RemoveFurnitureStates.select_furniture)
    await _render_furniture_list_page(callback, page=0)


@router.callback_query(F.data.startswith("remove_furniture_page:"))
async def change_remove_page(callback: types.CallbackQuery):
    await callback.answer()
    try:
        page = int(callback.data.split(":")[1])
    except (ValueError, IndexError):
        page = 0
    await _render_furniture_list_page(callback, page=page)


@router.callback_query(F.data == "noop_page")
async def noop_page_handler(callback: types.CallbackQuery):
    await callback.answer()


@router.callback_query(F.data.startswith("ask_delete:"))
async def ask_delete_furniture(callback: types.CallbackQuery):
    parsed = _parse_id_and_page(callback.data)
    if parsed is None:
        await callback.answer()
        return
    furniture_id, page = parsed

    item = await CrudFurniture().get_furniture_by_id(furniture_id)
    if not item:
        await callback.answer("⚠️ Товар уже удален или не найден.", show_alert=True)
        await _render_furniture_list_page(callback, page=page)
        return

    await callback.answer()

    confirm_buttons = [
        ("✅ Да, удалить", f"confirm_delete:{furniture_id}:{page}"),
        ("❌ Отмена", f"remove_furniture_page:{page}")
    ]

    text = (
        f"❓ <b>Подтверждение удаления товара #{item.id}</b>\n\n"
        f"📦 <b>Категория:</b> {escape(item.category_name)}\n"
        f"🌍 <b>Страна/Тип:</b> {escape(item.country_origin or '—')}\n"
        f"📝 <b>Описание:</b> {escape(_snippet(item.description))}\n\n"
        "Вы действительно хотите навсегда удалить этот товар и все его фотографии?"
    )

    await safe_edit_text(callback.message, text, make_row_inline_keyboards(confirm_buttons))


@router.callback_query(F.data.startswith("confirm_delete:"))
async def confirm_delete_furniture(callback: types.CallbackQuery):
    parsed = _parse_id_and_page(callback.data)
    if parsed is None:
        await callback.answer()
        return
    furniture_id, page = parsed

    deleted = await CrudFurniture().delete_furniture(furniture_id)
    if deleted:
        await callback.answer("✅ Товар успешно удален", show_alert=True)
    else:
        await callback.answer("❌ Не удалось удалить: возможно, товар уже был удален", show_alert=True)

    await _render_furniture_list_page(callback, page=page)
