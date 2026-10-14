from html import escape

from aiogram import Router, F, types

from database.crud import CrudCategory
from keyboard.keyboard_builder import make_row_inline_keyboards
from utils.messages import safe_edit_text

router = Router()

PAGE_SIZE = 8


def _parse_id_and_page(data: str) -> tuple[int, int] | None:
    parts = data.split(":")
    if len(parts) != 3:
        return None
    try:
        return int(parts[1]), int(parts[2])
    except ValueError:
        return None


async def _render_category_list_page(callback: types.CallbackQuery, page: int = 0):
    categories = await CrudCategory().get_all_categories()

    if not categories:
        back_kb = make_row_inline_keyboards([("⬅️ Назад в админ-панель", "settings_bot")])
        await safe_edit_text(callback.message, "📭 В базе нет категорий для удаления.", back_kb)
        return

    total_pages = (len(categories) + PAGE_SIZE - 1) // PAGE_SIZE
    page = max(0, min(page, total_pages - 1))
    page_items = categories[page * PAGE_SIZE:(page + 1) * PAGE_SIZE]

    buttons = [
        (f"🗂 {cat.name}", f"ask_delete_category:{cat.id}:{page}")
        for cat in page_items
    ]

    if page > 0:
        buttons.append(("◀️ Назад", f"remove_category_page:{page - 1}"))
    if total_pages > 1:
        buttons.append((f"Стр. {page + 1}/{total_pages}", "noop_page"))
    if page < total_pages - 1:
        buttons.append(("Вперёд ▶️", f"remove_category_page:{page + 1}"))
    buttons.append(("⬅️ В админ-панель", "settings_bot"))

    text = (
        f"🗂 <b>Удаление категории</b> (Всего категорий: {len(categories)})\n\n"
        "Выберите категорию для подтверждения удаления:"
    )
    await safe_edit_text(callback.message, text, make_row_inline_keyboards(buttons))


@router.callback_query(F.data == "remove_category")
async def show_categories_to_remove(callback: types.CallbackQuery):
    await callback.answer()
    await _render_category_list_page(callback, page=0)


@router.callback_query(F.data.startswith("remove_category_page:"))
async def change_remove_category_page(callback: types.CallbackQuery):
    await callback.answer()
    try:
        page = int(callback.data.split(":")[1])
    except (ValueError, IndexError):
        page = 0
    await _render_category_list_page(callback, page=page)


@router.callback_query(F.data.startswith("ask_delete_category:"))
async def ask_delete_category(callback: types.CallbackQuery):
    parsed = _parse_id_and_page(callback.data)
    if parsed is None:
        await callback.answer()
        return
    category_id, page = parsed

    crud = CrudCategory()
    category = await crud.get_category_by_id(category_id)
    if not category:
        await callback.answer("⚠️ Категория уже удалена или не найдена.", show_alert=True)
        await _render_category_list_page(callback, page=page)
        return

    await callback.answer()
    items_count = await crud.count_furniture_in_category(category.name)

    if items_count:
        warning = (
            f"⚠️ В категории <b>{items_count}</b> шт. товаров — они будут удалены "
            "вместе со всеми фотографиями.\n\n"
        )
    else:
        warning = "В категории нет товаров.\n\n"

    confirm_buttons = [
        ("✅ Да, удалить", f"confirm_delete_category:{category_id}:{page}"),
        ("❌ Отмена", f"remove_category_page:{page}"),
    ]
    text = (
        f"❓ <b>Удалить категорию «{escape(category.name)}»?</b>\n\n"
        f"{warning}"
        "Это действие нельзя отменить."
    )
    await safe_edit_text(callback.message, text, make_row_inline_keyboards(confirm_buttons))


@router.callback_query(F.data.startswith("confirm_delete_category:"))
async def confirm_delete_category(callback: types.CallbackQuery):
    parsed = _parse_id_and_page(callback.data)
    if parsed is None:
        await callback.answer()
        return
    category_id, page = parsed

    if await CrudCategory().delete_category(category_id):
        await callback.answer("✅ Категория удалена", show_alert=True)
    else:
        await callback.answer("❌ Не удалось удалить: возможно, категория уже была удалена", show_alert=True)

    await _render_category_list_page(callback, page=page)
