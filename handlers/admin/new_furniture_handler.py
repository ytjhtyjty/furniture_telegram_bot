import asyncio
from html import escape

from aiogram import Router, F, types
from aiogram.fsm.context import FSMContext
from states.states import NewFurnitureStates
from keyboard.keyboard_builder import make_row_keyboards, make_row_inline_keyboards
from keyboard.button_template import furniture_cancel_kb, country_of_origin_kb, kitchen_subcategory_inline_kb
from database.crud import CrudCategory, CrudFurniture
from .main_admin import show_admin_panel

router = Router()
_photo_lock = asyncio.Lock()

# 1. Старт создания мебели
@router.callback_query(F.data == "new_furniture")
async def start_add_furniture(callback: types.CallbackQuery, state: FSMContext):
    await state.clear()
    await state.set_state(NewFurnitureStates.description)
    await callback.message.answer(
        "🪑 <b>Добавление новой мебели</b>\n\n"
        "<b>Шаг 1:</b> Отправьте подробное описание товара в одном сообщении:\n"
        "• Название\n"
        "• Габариты (длина x ширина x высота)\n"
        "• Материал каркаса и обивки\n"
        "• Стоимость",
        reply_markup=make_row_inline_keyboards(furniture_cancel_kb)
    )
    await callback.answer()

# 2. Получение описания и динамическая выдача категорий из базы
@router.message(NewFurnitureStates.description)
async def process_furniture_description(message: types.Message, state: FSMContext):
    description = (message.text or "").strip()
    if not description:
        await message.answer("⚠️ Описание не может быть пустым. Попробуйте еще раз:")
        return

    await state.update_data(description=description)

    # ДИНАМИЧЕСКИ ДОСТАЕМ КАТЕГОРИИ ИЗ БАЗЫ ДАННЫХ
    crud = CrudCategory()
    categories_from_db = await crud.get_all_categories()

    if not categories_from_db:
        await message.answer("⚠️ В базе данных пока нет категорий! Сначала создайте категорию.")
        await state.clear()
        return

    # Собираем список названий категорий для клавиатуры
    category_names = [cat.name for cat in categories_from_db]
    category_buttons = category_names + ["❌ Отменить"]

    # Запоминаем, какие категории реально есть в базе, чтобы проверить выбор на шаге 3
    await state.update_data(category_names=category_names)
    await state.set_state(NewFurnitureStates.category)
    await message.answer(
        "<b>Шаг 2:</b> Выберите категорию для мебели из кнопок ниже:",
        reply_markup=make_row_keyboards(category_buttons)
    )

# 3. Обработка категории и умное ветвление (Кухня vs Остальное)
@router.message(NewFurnitureStates.category)
async def process_furniture_category(message: types.Message, state: FSMContext):
    category_name = (message.text or "").strip()

    if category_name == "❌ Отменить":
        await state.clear()
        await message.answer("🚫 Добавление отменено.", reply_markup=types.ReplyKeyboardRemove())
        # Возвращаем админа в админ-панель
        await show_admin_panel(message, state)
        return

    # Принимаем только категории, которые есть в базе (список сохранён на шаге 2)
    data = await state.get_data()
    if category_name not in data.get("category_names", []):
        await message.answer("⚠️ Такой категории нет. Выберите категорию кнопкой из списка ниже.")
        return

    await state.update_data(category=category_name)
    # Убираем клавиатуру с категориями
    await message.answer(
        f"✅ Категория: <b>{escape(category_name)}</b>",
        reply_markup=types.ReplyKeyboardRemove()
    )

    # Проверяем, кухня ли это
    if "кухонная" in category_name.lower() or "кухн" in category_name.lower():
        # Для кухонь страна по ТЗ всегда Россия, но выбираем форму
        await state.update_data(country="Россия")
        await state.set_state(NewFurnitureStates.kitchen_type)
        await message.answer(
            "📐 Выберите тип кухонного гарнитура:",
            reply_markup=make_row_inline_keyboards(kitchen_subcategory_inline_kb)
        )
    else:
        # Для остальных спрашиваем страну
        await state.set_state(NewFurnitureStates.country)
        await message.answer(
            "🌍 Выберите страну производства:",
            reply_markup=make_row_inline_keyboards(country_of_origin_kb)
        )

# 4а. Обработка формы кухни (Прямая / Угловая / Назад)
@router.callback_query(
    NewFurnitureStates.kitchen_type,
    F.data.in_({"straight_kitchen", "corner_kitchen", "back_to_main"})
)
async def process_kitchen_type(callback: types.CallbackQuery, state: FSMContext):
    await callback.answer()
    if callback.data == "back_to_main":
        await state.clear()
        await show_admin_panel(callback.message, state)
        return

    kitchen_type = "Прямая кухня" if callback.data == "straight_kitchen" else "Угловая кухня"
    await state.update_data(kitchen_type=kitchen_type)
    await init_photo_upload(callback.message, state)

# 4б. Обработка страны (Россия / Турция / Назад)
@router.callback_query(
    NewFurnitureStates.country,
    F.data.in_({"russian_origin", "turkey_origin", "back_to_main"})
)
async def process_country(callback: types.CallbackQuery, state: FSMContext):
    await callback.answer()
    if callback.data == "back_to_main":
        await state.clear()
        await show_admin_panel(callback.message, state)
        return

    country = "Россия" if callback.data == "russian_origin" else "Турция"
    await state.update_data(country=country)
    await init_photo_upload(callback.message, state)

# 5. Переход к загрузке фото
async def init_photo_upload(message: types.Message, state: FSMContext):
    await state.set_state(NewFurnitureStates.photos)
    await state.update_data(photos=[])  # Создаем пустой список для file_id

    finish_kb = [
        ("✅ Завершить добавление", "finish_furniture_creation"),
        ("❌ Отменить", "cancel_furniture")
    ]
    await message.answer(
        "📸 <b>Шаг 3: Загрузка фотографий</b>\n\n"
        "Отправьте от 1 до 10 фотографий мебели.\n"
        "Когда закончите отправку, нажмите кнопку <b>«Завершить добавление»</b>.",
        reply_markup=make_row_inline_keyboards(finish_kb)
    )

# 6. Прием каждого фото и сбор file_id в память FSM
@router.message(NewFurnitureStates.photos, F.photo)
async def process_incoming_photo(message: types.Message, state: FSMContext):
    async with _photo_lock:
        data = await state.get_data()
        photos = data.get("photos", [])

        if len(photos) >= 10:
            await message.answer("⚠️ Достигнут лимит (максимум 10 фотографий). Нажмите «Завершить добавление».")
            return

        # Берем фото в самом высоком качестве (последний элемент массива)
        best_photo_file_id = message.photo[-1].file_id
        if best_photo_file_id not in photos:
            photos.append(best_photo_file_id)
            await state.update_data(photos=photos)
            await message.answer(f"📸 Фото принято ({len(photos)} из 10). Отправьте еще или завершите.")

# 7. Финал: сохранение товара и всех фото в базу
@router.callback_query(F.data == "finish_furniture_creation")
async def finish_furniture_save(callback: types.CallbackQuery, state: FSMContext):
    await callback.answer()
    data = await state.get_data()

    if not data or "category" not in data:
        await callback.message.answer("⚠️ Данные устарели или не найдены. Начните добавление мебели сначала.")
        await state.clear()
        return

    photos = data.get("photos", [])
    if not photos:
        await callback.message.answer("⚠️ Нельзя создать товар без фотографий! Отправьте хотя бы 1 фото.")
        return

    desc = data.get("description", "")
    kitchen_type = data.get("kitchen_type")
    if kitchen_type:
        desc = f"[{kitchen_type}] {desc}"

    crud = CrudFurniture()
    furniture = await crud.create_furniture(
        description=desc,
        category=data["category"],
        country=data.get("country", "Россия"),
        photos=photos
    )

    if not furniture:
        await callback.message.answer("❌ Ошибка базы данных при сохранении мебели.")
        await state.clear()
        return

    await state.clear()

    await callback.message.answer(
        "🎉 <b>Мебель успешно добавлена в каталог!</b>\n\n"
        f"📦 <b>Категория:</b> {escape(data['category'])}\n"
        f"🌍 <b>Страна/Тип:</b> {escape(data.get('kitchen_type') or data.get('country') or '—')}\n"
        f"🖼 <b>Количество фото:</b> {len(photos)} шт.\n\n"
        f"📝 <b>Описание:</b>\n{escape(desc)}"
    )

    # Возвращаем админа в админ-панель
    await show_admin_panel(callback.message, state)

# 8. Отмена
@router.callback_query(F.data == "cancel_furniture")
async def cancel_furniture_handler(callback: types.CallbackQuery, state: FSMContext):
    await state.clear()
    await callback.answer()
    await callback.message.edit_text("🚫 Добавление мебели отменено.")
    # Возвращаем админа в админ-панель
    await show_admin_panel(callback.message, state)