from aiogram import Router, F, types
from database.crud import CrudCategory

router = Router()

@router.callback_query(F.data == "list_categories_furniture")
async def list_categories_handler(callback: types.CallbackQuery):
    crud = CrudCategory()
    categories = await crud.get_all_categories()

    if not categories:
        await callback.message.answer("📭 В базе пока нет ни одной категории.")
        await callback.answer()
        return

    text = "📋 <b>Список всех категорий мебели:</b>\n\n"
    for idx, cat in enumerate(categories, start=1):
        desc = f" — <i>{cat.description}</i>" if cat.description else ""
        text += f"{idx}. <b>{cat.name}</b>{desc}\n"

    await callback.message.answer(text)
    await callback.answer()