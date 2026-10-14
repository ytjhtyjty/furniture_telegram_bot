import logging
import re
from html import escape

from aiogram import Router, F, types
from aiogram.exceptions import TelegramAPIError
from aiogram.filters import Command, CommandStart
from aiogram.fsm.context import FSMContext

from database.crud import CrudCategory, CrudUser, CrudCooperation
from states.states import CooperationStates
from keyboard.keyboard_builder import make_row_inline_keyboards
from settings.config import ConfigBot
from utils.filters import NotCommand
from utils.messages import contacts_block, safe_edit_text

logger = logging.getLogger(__name__)
router = Router()


INTRO_TEXT = (
    "🌟 <b>Добро пожаловать в наш мебельный бот!</b> 🌟\n\n"
    "🛋 Здесь вы найдёте стильную и качественную мебель "
    "для любого интерьера.\n\n"
    "🛒 <b>Как сделать заказ:</b>\n"
    "1. Выберите категорию мебели\n"
    "2. Просмотрите модели\n"
    "3. Свяжитесь с нами для заказа\n\n"
    "🔙 В любой момент можно вернуться «Назад».\n\n"
)
CHOOSE_TEXT = "👇 <b>Выберите категорию из меню ниже:</b>"
EMPTY_TEXT = "📭 Каталог пока пуст, загляните позже."

NAME_MAX = 100
MESSAGE_MAX = 1000
PHONE_ALLOWED = re.compile(r"^[\d\s()+\-]+$")


async def build_main_menu(user_id: int) -> tuple[str, types.InlineKeyboardMarkup]:
    categories = await CrudCategory().get_all_categories()
    items = [(cat.name, f"category:{cat.id}") for cat in categories]

    items.append(("ℹ️ О компании / Контакты", "about_company"))
    items.append(("🤝 Сотрудничество", "cooperation_company"))

    if user_id in ConfigBot.ADMIN_IDS:
        items.append(("⚙️ Настройки бота", "settings_bot"))

    text = INTRO_TEXT + (CHOOSE_TEXT if categories else EMPTY_TEXT)
    return text, make_row_inline_keyboards(items)


@router.message(CommandStart())
async def cmd_start(message: types.Message, state: FSMContext):
    await state.clear()

    await CrudUser().get_or_create_user(
        telegram_id=message.from_user.id,
        username=message.from_user.username,
        firstname=message.from_user.first_name,
        lastname=message.from_user.last_name,
        is_admin=message.from_user.id in ConfigBot.ADMIN_IDS,
    )

    text, keyboard = await build_main_menu(message.from_user.id)
    await message.answer(text, reply_markup=keyboard)


@router.callback_query(F.data == "back_to_main")
async def back_to_main(callback: types.CallbackQuery, state: FSMContext):
    await state.clear()
    await callback.answer()
    text, keyboard = await build_main_menu(callback.from_user.id)
    await safe_edit_text(callback.message, text, keyboard)


@router.callback_query(F.data == "about_company")
async def about_company_handler(callback: types.CallbackQuery):
    await callback.answer()
    back_kb = make_row_inline_keyboards([("⬅️ Назад", "back_to_main")])
    contacts = contacts_block()
    text = (
        "ℹ️ <b>О компании:</b>\n\n"
        "Мы предлагаем качественную мебель для дома и офиса "
        "по доступным ценам.\n"
        "📞 Свяжитесь с нами для консультации и оформления заказа."
    )
    if contacts:
        text += "\n\n" + contacts
    await safe_edit_text(callback.message, text, back_kb)


def _cooperation_cancel_kb() -> types.InlineKeyboardMarkup:
    return make_row_inline_keyboards([
        ("❌ Отмена", "cooperation_cancel"),
    ])


def _is_valid_phone(phone: str) -> bool:
    if not PHONE_ALLOWED.match(phone):
        return False
    digits = sum(ch.isdigit() for ch in phone)
    return 10 <= digits <= 15


async def _notify_admins(bot, name: str, phone: str, text: str | None, user: types.User) -> None:
    username = f" (@{escape(user.username)})" if user.username else ""
    notification = (
        "🔔 <b>Новая заявка на сотрудничество</b>\n\n"
        f"👤 {escape(name)}{username}\n"
        f"📞 {escape(phone)}\n"
        f"📝 {escape(text or '—')}"
    )
    kb = make_row_inline_keyboards([("🤝 Открыть заявки", "cooperation_requests")])
    for admin_id in ConfigBot.ADMIN_IDS:
        try:
            await bot.send_message(admin_id, notification, reply_markup=kb)
        except TelegramAPIError:
            logger.warning("Не удалось уведомить админа %s о заявке", admin_id)


@router.callback_query(F.data == "cooperation_company")
async def cooperation_start(callback: types.CallbackQuery, state: FSMContext):
    await callback.answer()
    await state.clear()
    await state.set_state(CooperationStates.name)
    await safe_edit_text(
        callback.message,
        "🤝 <b>Сотрудничество</b>\n\n"
        "Оставьте заявку, и мы свяжемся с вами.\n\n"
        "Введите ваше <b>имя</b>:",
        _cooperation_cancel_kb(),
    )


@router.message(CooperationStates.name, NotCommand())
async def cooperation_name(message: types.Message, state: FSMContext):
    name = (message.text or "").strip()
    if not name or len(name) > NAME_MAX:
        await message.answer(
            f"⚠️ Введите корректное имя (до {NAME_MAX} символов):",
            reply_markup=_cooperation_cancel_kb(),
        )
        return
    await state.update_data(name=name)
    await state.set_state(CooperationStates.phone)
    await message.answer(
        "📞 Введите ваш <b>телефон</b>:",
        reply_markup=_cooperation_cancel_kb(),
    )


@router.message(CooperationStates.phone, NotCommand())
async def cooperation_phone(message: types.Message, state: FSMContext):
    phone = message.contact.phone_number if message.contact else (message.text or "").strip()
    if not phone or not _is_valid_phone(phone):
        await message.answer(
            "⚠️ Введите корректный телефон, например: <code>+7 900 123-45-67</code>",
            reply_markup=_cooperation_cancel_kb(),
        )
        return
    await state.update_data(phone=phone)
    await state.set_state(CooperationStates.message)
    await message.answer(
        "📝 Коротко опишите, что вас интересует:\n\n"
        "(Например: «Хочу оптом», «Дизайнер», «Партнёрство»)",
        reply_markup=_cooperation_cancel_kb(),
    )


@router.message(CooperationStates.message, NotCommand())
async def cooperation_message(message: types.Message, state: FSMContext):
    text = (message.text or "").strip()
    data = await state.get_data()
    await state.clear()

    if "name" not in data or "phone" not in data:
        await message.answer("⚠️ Данные заявки устарели. Начните заново.")
    else:
        text = text[:MESSAGE_MAX] if text else None
        ok = await CrudCooperation().create_request(
            name=data["name"],
            phone=data["phone"],
            message=text,
        )

        if ok:
            await message.answer(
                "✅ <b>Заявка отправлена!</b>\n\n"
                "Мы свяжемся с вами в ближайшее время."
            )
            await _notify_admins(message.bot, data["name"], data["phone"], text, message.from_user)
        else:
            await message.answer(
                "❌ Не удалось отправить заявку. Попробуйте позже."
            )

    menu_text, menu_kb = await build_main_menu(message.from_user.id)
    await message.answer(menu_text, reply_markup=menu_kb)


@router.callback_query(F.data == "cooperation_cancel")
async def cooperation_cancel(callback: types.CallbackQuery, state: FSMContext):
    await callback.answer()
    await state.clear()
    menu_text, menu_kb = await build_main_menu(callback.from_user.id)
    await safe_edit_text(callback.message, menu_text, menu_kb)


@router.message(Command("admin_panel"))
async def admin_panel_denied(message: types.Message):
    await message.answer("⛔ У вас нет доступа к панели администратора.")


@router.callback_query(F.data == "settings_bot")
async def settings_denied(callback: types.CallbackQuery):
    await callback.answer("⛔ У вас нет доступа.", show_alert=True)
