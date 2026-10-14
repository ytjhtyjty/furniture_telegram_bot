from aiogram import Router

from . import catalog, start

router = Router()
router.include_router(start.router)
router.include_router(catalog.router)