from aiogram.types import ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardMarkup, InlineKeyboardButton

def make_row_keyboards(items: list[str]) -> ReplyKeyboardMarkup:
    keyboard = [[KeyboardButton(text=item)] for item in items]
    return ReplyKeyboardMarkup(keyboard=keyboard, resize_keyboard=True)

def make_row_inline_keyboards(items: list[tuple[str, str]]) -> InlineKeyboardMarkup:
    keyboard = []
    for text, callback_data in items:
        keyboard.append([InlineKeyboardButton(text=text, callback_data=callback_data)])
    return InlineKeyboardMarkup(inline_keyboard=keyboard)