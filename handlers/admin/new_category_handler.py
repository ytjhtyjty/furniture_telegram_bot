from aiogram import Router, F, types
from aiogram.fsm.context import FSMContext
from states.states import NewCategoryStates
from keyboard.keyboard_builder import make_row_inline_keyboards
from keyboard.button_template import build_cancel_kb
from database.crud import CrudCategory

router = Router()

# 1. Старт создания категории
@router.callback_query(F.data == "new_category_furniture")
async def start_add_category(callback: types.CallbackQuery, state: FSMContext):
    await state.clear()
    await state.set_state(NewCategoryStates.name_category)
    await callback.message.answer(
        "➕ <b>Добавление новой категории</b>\n\n"
        "Введите название категории (например: <i>Диваны</i> или <i>Офисная мебель</i>):",
        reply_markup=make_row_inline_keyboards(build_cancel_kb)
    )
    await callback.answer()

# 2. Прием названия категории
@router.message(NewCategoryStates.name_category)
async def process_category_name(message: types.Message, state: FSMContext):
    name = message.text.strip()
    if not name:
        await message.answer("⚠️ Название не может быть пустым. Введите название:")
        return

    await state.update_data(name=name)
    await state.set_state(NewCategoryStates.description_category)
    await message.answer(
        f"Отлично! Название: <b>{name}</b>.\n\n"
        "Теперь введите краткое описание категории (2-3 слова):",
        reply_markup=make_row_inline_keyboards(build_cancel_kb)
    )

# 3. Прием описания и подтверждение
@router.message(NewCategoryStates.description_category)
async def process_category_description(message: types.Message, state: FSMContext):
    description = message.text.strip()
    await state.update_data(description=description)
    data = await state.get_data()

    confirm_kb = [
        ("✅ Подтвердить", "confirm_add_category"),
        ("❌ Отменить", "cancel_category")
    ]

    await message.answer(
        "🔍 <b>Проверьте данные новой категории:</b>\n\n"
        f"🏷 <b>Название:</b> {data['name']}\n"
        f"📝 <b>Описание:</b> {description}\n\n"
        "Сохранить эту категорию в базу?",
        reply_markup=make_row_inline_keyboards(confirm_kb)
    )

# 4. Финальная запись в базу
@router.callback_query(F.data == "confirm_add_category")
async def confirm_category_save(callback: types.CallbackQuery, state: FSMContext):
    data = await state.get_data()
    if not data or 'name' not in data:
        await callback.message.answer("⚠️ Данные устарели. Начните сначала.")
        await state.clear()
        return

    crud = CrudCategory()
    success = await crud.create_category(name=data['name'], description=data.get('description', ''))

    if success:
        await callback.message.answer(f"🎉 Категория <b>{data['name']}</b> успешно сохранена в базе данных!")
    else:
        await callback.message.answer("❌ Ошибка: возможно категория с таким именем уже существует.")

    await state.clear()
    await callback.answer()

# 5. Отмена в любой момент
@router.callback_query(F.data == "cancel_category")
async def cancel_category_handler(callback: types.CallbackQuery, state: FSMContext):
    await state.clear()
    await callback.message.answer("🚫 Добавление категории отменено.")
    await callback.answer()