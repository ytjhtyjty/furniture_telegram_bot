import logging
from typing import Optional
from sqlalchemy import select
from sqlalchemy.orm import selectinload
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from database.engine import AsyncSessionLocal
from database.models import Category, Furniture, FurniturePhoto, User

logger = logging.getLogger(__name__)


class CrudCategory:
    def __init__(self):
        self.session = AsyncSessionLocal

    # Получить список абсолютно всех категорий из базы
    async def get_all_categories(self) -> list[Category]:
        async with self.session() as session:
            try:
                stmt = select(Category)
                result = await session.execute(stmt)
                return list(result.scalars().all())
            except SQLAlchemyError:
                logger.exception("Ошибка при получении всех категорий")
                return []

    # Добавить новую категорию
    async def create_category(self, name: str, description: str) -> bool:
        async with self.session() as session:
            try:
                new_cat = Category(name=name, description=description)
                session.add(new_cat)
                await session.commit()
                logger.info("Создана категория: %s", name)
                return True
            except IntegrityError:
                await session.rollback()
                logger.warning("Дубликат категории: %s", name)
                return False
            except SQLAlchemyError:
                await session.rollback()
                logger.exception("Ошибка БД при создании категории")
                return False


class CrudFurniture:
    def __init__(self):
        self.session = AsyncSessionLocal

    # Добавить товар (мебель)
    async def create_furniture(self, description: str, category: str, country: str) -> Optional[Furniture]:
        async with self.session() as session:
            try:
                item = Furniture(
                    description=description,
                    category_name=category,
                    country_origin=country
                )
                session.add(item)
                await session.commit()
                await session.refresh(item)
                return item
            except SQLAlchemyError:
                await session.rollback()
                logger.exception("Ошибка при создании мебели")
                return None

    # Привязать пачку фотографий (file_id) к товару
    async def add_photos_to_furniture(self, furniture_id: int, photos: list[str]) -> bool:
        if not photos:
            return True

        async with self.session() as session:
            try:
                # Пакетная вставка вместо цикла session.add()
                photo_objects = [
                    FurniturePhoto(furniture_id=furniture_id, file_id=file_id)
                    for file_id in photos
                ]
                session.add_all(photo_objects)
                await session.commit()
                return True
            except SQLAlchemyError:
                await session.rollback()
                logger.exception("Ошибка сохранения фото для мебели ID %s", furniture_id)
                return False
    
    # Получить мебель по категории и стране с предзагрузкой фото
    async def get_furniture(self, category: str, country: Optional[str] = None) -> list[Furniture]:
        async with self.session() as session:
            try:
                stmt = (
                    select(Furniture)
                    .options(selectinload(Furniture.photos))
                    .where(Furniture.category_name == category)
                )

                if country:
                    stmt = stmt.where(Furniture.country_origin == country)
                
                result = await session.execute(stmt)
                return list(result.scalars().all())
            except SQLAlchemyError:
                logger.exception("Ошибка при получении мебели для категории %s", category)
                return []