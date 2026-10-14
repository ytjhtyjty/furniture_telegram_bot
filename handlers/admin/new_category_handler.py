from html import escape

from aiogram import Router, F, types
from aiogram.fsm.context import FSMContext
from states.states import NewCategoryStates
from keyboard.keyboard_builder import make_row_inline_keyboards
from keyboard.button_template import build_cancel_kb, furniture_types_kb, skip_description_kb
from database.crud import CrudCategory
from utils.catalog_utils import CATEGORY_DESCRIPTION_MAX, CATEGORY_NAME_MAX
from utils.filters import NotCommand
from utils.messages import safe_edit_text
from .main_admin import show_admin_panel

router = Router()

FURNITURE_TYPE_TITLES = dict((cb, text) for text, cb in furniture_types_kb)


async def _ask_confirmation(message: types.Message, state: FSMContext) -> None:
    data = await state.get_data()
    description = data.get("description")

    confirm_kb = [
        ("✅ Подтвердить", "confirm_add_category"),
        ("❌ Отменить", "cancel_category")
    ]

    await message.answer(
        "🔍 <b>Проверьте данные новой категории:</b>\n\n"
        f"🏷 <b>Название:</b> {escape(data['name'])}\n"
        f"🗂 <b>Тип мебели:</b> {escape(FURNITURE_TYPE_TITLES.get(data.get('furniture_type'), '—'))}\n"
        f"📝 <b>Описание:</b> {escape(description) if description else '—'}\n\n"
        "Сохранить эту категорию в базу?",
        reply_markup=make_row_inline_keyboards(confirm_kb)
    )


@router.callback_query(F.data == "new_category_furniture")
async def start_add_category(callback: types.CallbackQuery, state: FSMContext):
    await callback.answer()
    await state.clear()
    await state.set_state(NewCategoryStates.name_category)
    await callback.message.answer(
        "➕ <b>Добавление новой категории</b>\n\n"
        "Введите название категории (например: <i>Диваны</i> или <i>Офисная мебель</i>):",
        reply_markup=make_row_inline_keyboards(build_cancel_kb)
    )


@router.message(NewCategoryStates.name_category, NotCommand())
async def process_category_name(message: types.Message, state: FSMContext):
    name = (message.text or "").strip()
    if not name:
        await message.answer(
            "⚠️ Название не может быть пустым. Введите название:",
            reply_markup=make_row_inline_keyboards(build_cancel_kb)
        )
        return

    if len(name) > CATEGORY_NAME_MAX:
        await message.answer(
            f"⚠️ Название слишком длинное (максимум {CATEGORY_NAME_MAX} символов). Введите короче:",
            reply_markup=make_row_inline_keyboards(build_cancel_kb)
        )
        return

    if await CrudCategory().check_category_by_name(name):
        await message.answer(
            "⚠️ Категория с таким именем уже существует в базе! Введите другое название:",
            reply_markup=make_row_inline_keyboards(build_cancel_kb)
        )
        return

    await state.update_data(name=name)
    await state.set_state(NewCategoryStates.furniture_type)
    await message.answer(
        f"Отлично! Название: <b>{escape(name)}</b>.\n\n"
        "Теперь выберите <b>тип мебели</b> кнопкой ниже:",
        reply_markup=make_row_inline_keyboards(furniture_types_kb + build_cancel_kb)
    )


@router.callback_query(NewCategoryStates.furniture_type, F.data.in_(set(FURNITURE_TYPE_TITLES)))
async def process_category_type(callback: types.CallbackQuery, state: FSMContext):
    await callback.answer()
    await state.update_data(furniture_type=callback.data)
    await state.set_state(NewCategoryStates.description_category)
    await callback.message.edit_text(
        f"🗂 Тип мебели: <b>{escape(FURNITURE_TYPE_TITLES[callback.data])}</b>\n\n"
        f"Введите краткое описание категории (до {CATEGORY_DESCRIPTION_MAX} символов) "
        "или нажмите «Пропустить»:",
        reply_markup=make_row_inline_keyboards(skip_description_kb + build_cancel_kb)
    )


@router.message(NewCategoryStates.furniture_type, NotCommand())
async def process_category_type_text(message: types.Message):
    await message.answer(
        "⚠️ Выберите тип мебели кнопкой из списка выше.",
        reply_markup=make_row_inline_keyboards(furniture_types_kb + build_cancel_kb)
    )


@router.message(NewCategoryStates.description_category, NotCommand())
async def process_category_description(message: types.Message, state: FSMContext):
    description = (message.text or "").strip()
    if not description:
        await message.answer(
            "⚠️ Описание не может быть пустым. Введите описание или нажмите «Пропустить»:",
            reply_markup=make_row_inline_keyboards(skip_description_kb + build_cancel_kb)
        )
        return

    if len(description) > CATEGORY_DESCRIPTION_MAX:
        await message.answer(
            f"⚠️ Описание слишком длинное (максимум {CATEGORY_DESCRIPTION_MAX} символов). Введите короче:",
            reply_markup=make_row_inline_keyboards(skip_description_kb + build_cancel_kb)
        )
        return

    await state.update_data(description=description)
    await _ask_confirmation(message, state)


@router.callback_query(NewCategoryStates.description_category, F.data == "skip_category_description")
async def skip_category_description(callback: types.CallbackQuery, state: FSMContext):
    await callback.answer()
    await state.update_data(description=None)
    await _ask_confirmation(callback.message, state)


@router.callback_query(F.data == "confirm_add_category")
async def confirm_category_save(callback: types.CallbackQuery, state: FSMContext):
    await callback.answer()
    data = await state.get_data()
    await state.clear()

    if not data or 'name' not in data or 'furniture_type' not in data:
        await callback.message.answer("⚠️ Данные устарели. Начните сначала.")
        return

    crud = CrudCategory()
    if await crud.check_category_by_name(data['name']):
        await callback.message.edit_text("❌ Категория с таким именем уже существует.")
    elif await crud.create_category(
        name=data['name'],
        description=data.get('description'),
        furniture_type=data['furniture_type'],
    ):
        await callback.message.edit_text("✅ Категория сохранена в базе")
    else:
        await callback.message.edit_text("❌ Ошибка базы данных: категория не сохранена.")

    await show_admin_panel(callback.message, state, admin=callback.from_user)


@router.callback_query(F.data == "cancel_category")
async def cancel_category_handler(callback: types.CallbackQuery, state: FSMContext):
    already_cancelled = await state.get_state() is None
    await callback.answer()
    if already_cancelled:
        return
    await state.clear()
    await safe_edit_text(callback.message, "🚫 Добавление категории отменено.")
    await show_admin_panel(callback.message, state, admin=callback.from_user)
