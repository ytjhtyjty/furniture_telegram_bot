from aiogram import Router
from . import main_admin, list_category_furniture_handler, new_category_handler, new_furniture_handler

router = Router()

# Подключаем все части админки к главному роутеру
router.include_router(main_admin.router)
router.include_router(list_category_furniture_handler.router)
router.include_router(new_category_handler.router)
router.include_router(new_furniture_handler.router)