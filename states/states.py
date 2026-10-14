from aiogram.fsm.state import State, StatesGroup


class NewCategoryStates(StatesGroup):
    name_category = State()
    furniture_type = State()
    description_category = State()


class NewFurnitureStates(StatesGroup):
    category = State()
    kitchen_type = State()
    country = State()
    description = State()
    photos = State()


class RemoveFurnitureStates(StatesGroup):
    select_furniture = State()


class CooperationStates(StatesGroup):
    name = State()
    phone = State()
    message = State()
