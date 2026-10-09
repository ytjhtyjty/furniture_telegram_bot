from typing import List, Tuple
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardMarkup, InlineKeyboardButton

# Делает обычные текстовые кнопки внизу экрана (Reply)
def make_row_keyboards(items: List[str]) -> ReplyKeyboardMarkup:
    keyboard = [[KeyboardButton(text=item)] for item in items]
    return ReplyKeyboardMarkup(keyboard=keyboard, resize_keyboard=True)

# Делает красивые инлайн-кнопки прямо под сообщением (Inline)
def make_row_inline_keyboards(items: List[Tuple[str, str]]) -> InlineKeyboardMarkup:
    keyboard = []
    # Каждая кнопка получает видимый текст и скрытый сигнал (callback_data)
    for text, callback_data in items:
        keyboard.append([InlineKeyboardButton(text=text, callback_data=callback_data)])
    return InlineKeyboardMarkup(inline_keyboard=keyboard)