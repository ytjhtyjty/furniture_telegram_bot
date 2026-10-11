from aiogram import Router, F, types

from database.crud import CrudFurniture
from keyboard.keyboard_builder import make_row_inline_keyboards
from .main_admin import show_admin_panel

router = Router()

# Telegram не принимает больше 100 кнопок в одной клавиатуре
MAX_ITEMS = 50
SNIPPET_LEN = 30


def _snippet(description: str | None) -> str:
    """Первая строка описания, обрезанная до SNIPPET_LEN символов."""
    text = (description or "").strip().splitlines()[0:1]
    text = text[0].strip() if text else "без описания"
    return text if len(text) <= SNIPPET_LEN else text[:SNIPPET_LEN].rstrip() + "…"


# 1. Показать список мебели кнопками
@router.callback_query(F.data == "remove_furniture")
async def show_furniture_to_remove(callback: types.CallbackQuery):
    items = await CrudFurniture().get_all_furniture()

    if not items:
        await callback.message.answer("📭 Каталог пуст")
        await callback.answer()
        return

    buttons = [
        (f"{item.id}. {_snippet(item.description)}", f"delete_item:{item.id}")
        for item in items[:MAX_ITEMS]
    ]
    buttons.append(("⬅️ Назад", "settings_bot"))

    text = "🗑 <b>Удаление мебели</b>\n\nВыберите товар, который нужно удалить:"
    if len(items) > MAX_ITEMS:
        text += f"\n\n<i>Показаны первые {MAX_ITEMS} из {len(items)}.</i>"

    await callback.message.answer(text, reply_markup=make_row_inline_keyboards(buttons))
    await callback.answer()


# 2. Удалить выбранный товар
@router.callback_query(F.data.startswith("delete_item:"))
async def delete_selected_furniture(callback: types.CallbackQuery):
    try:
        furniture_id = int(callback.data.split(":", 1)[1])
    except ValueError:
        await callback.answer("⚠️ Некорректный ID", show_alert=True)
        return

    deleted = await CrudFurniture().delete_furniture(furniture_id)

    if deleted:
        await callback.message.edit_text("✅ Мебель удалена")
    else:
        await callback.message.edit_text("❌ Не удалось удалить: возможно, мебель уже удалена.")

    # Возвращаем админа в админ-панель
    await show_admin_panel(callback.message)
    await callback.answer()
