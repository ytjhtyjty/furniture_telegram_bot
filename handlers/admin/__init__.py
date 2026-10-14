from aiogram import Router

from utils.filters import IsAdmin
from . import (
    main_admin,
    list_category_furniture_handler,
    new_category_handler,
    new_furniture_handler,
    remove_furniture_handler,
    remove_category_handler,
    cooperation_requests_handler,
)

router = Router()

router.message.filter(IsAdmin())
router.callback_query.filter(IsAdmin())

router.include_router(main_admin.router)
router.include_router(list_category_furniture_handler.router)
router.include_router(new_category_handler.router)
router.include_router(new_furniture_handler.router)
router.include_router(remove_furniture_handler.router)
router.include_router(remove_category_handler.router)
router.include_router(cooperation_requests_handler.router)
