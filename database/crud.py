import logging
from typing import Optional, List
from sqlalchemy import select
from sqlalchemy.orm import selectinload
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from database.engine import AsyncSessionLocal
from database.models import Category, Furniture, FurniturePhoto

class CrudCategory:
    def __init__(self):
        self.session = AsyncSessionLocal

    # Получить список абсолютно всех категорий из базы
    async def get_all_categories(self) -> List[Category]:
        async with self.session() as session:
            try:
                stmt = select(Category)
                result = await session.execute(stmt)
                all_categories = result.scalars().all()
                return list(all_categories) if all_categories else []
            except SQLAlchemyError as exc:
                logging.exception("Ошибка при получении всех категорий: %s", exc)
                return []

    # Добавить новую категорию
    async def create_category(self, name: str, description: str) -> bool:
        async with self.session() as session:
            try:
                new_cat = Category(name=name, description=description)
                session.add(new_cat)
                await session.commit()
                logging.info(f"Создана категория: {name}")
                return True
            except IntegrityError as exc:
                await session.rollback() # Откат, если категория уже существует
                logging.error(f"Дубликат категории: {exc}")
                return False
            except SQLAlchemyError as exc:
                await session.rollback()
                logging.exception(f"Ошибка БД: {exc}")
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
                await session.refresh(item) # Обновляем объект, чтобы получить присвоенный ID
                return item
            except SQLAlchemyError as exc:
                await session.rollback()
                logging.exception(f"Ошибка при создании мебели: {exc}")
                return None

    # Привязать пачку фотографий (file_id) к товару
    async def add_photos_to_furniture(self, furniture_id: int, photos: list[str]) -> bool:
        async with self.session() as session:
            try:
                for file_id in photos:
                    photo_obj = FurniturePhoto(furniture_id=furniture_id, file_id=file_id)
                    session.add(photo_obj)
                await session.commit()
                return True
            except SQLAlchemyError as exc:
                await session.rollback()
                logging.exception(f"Ошибка сохранения фото: {exc}")
                return False
    
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
                furniture_list = result.scalars().all()
                return list(furniture_list) if furniture_list else []
            except SQLAlchemyError as exc:
                logging.exception("Ошибка при получении мебели: %s", exc)
                return []