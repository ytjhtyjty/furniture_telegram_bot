import logging
from typing import Optional
from sqlalchemy import func, select
from sqlalchemy.orm import selectinload
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from database.engine import AsyncSessionLocal
from database.models import Category, Cooperation, Furniture, FurniturePhoto, User

logger = logging.getLogger(__name__)


class CrudCategory:
    def __init__(self):
        self.session = AsyncSessionLocal

    async def get_all_categories(self) -> list[Category]:
        async with self.session() as session:
            try:
                stmt = select(Category).order_by(Category.id)
                result = await session.execute(stmt)
                return list(result.scalars().all())
            except SQLAlchemyError:
                logger.exception("Ошибка при получении всех категорий")
                return []

    async def create_category(
        self,
        name: str,
        description: Optional[str] = None,
        furniture_type: Optional[str] = None,
    ) -> bool:
        async with self.session() as session:
            try:
                new_cat = Category(name=name, description=description, furniture_type=furniture_type)
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

    async def get_category_by_id(self, category_id: int) -> Optional[Category]:
        async with self.session() as session:
            try:
                stmt = select(Category).where(Category.id == category_id)
                result = await session.execute(stmt)
                return result.scalar_one_or_none()
            except SQLAlchemyError:
                logger.exception("Ошибка при получении категории по ID: %s", category_id)
                return None

    async def check_category_by_name(self, name: str) -> bool:
        async with self.session() as session:
            try:
                result = await session.execute(select(Category.name))
                target = name.strip().casefold()
                return any(existing.strip().casefold() == target for existing in result.scalars())
            except SQLAlchemyError:
                logger.exception("Ошибка при проверке категории: %s", name)
                return False

    async def count_furniture_in_category(self, name: str) -> int:
        async with self.session() as session:
            try:
                stmt = select(func.count(Furniture.id)).where(Furniture.category_name == name)
                return (await session.execute(stmt)).scalar_one() or 0
            except SQLAlchemyError:
                logger.exception("Ошибка при подсчёте товаров категории %s", name)
                return 0

    async def delete_category(self, category_id: int) -> bool:
        async with self.session() as session:
            try:
                category = await session.get(Category, category_id)
                if not category:
                    logger.warning("Категория с ID %s не найдена для удаления", category_id)
                    return False

                items = await session.execute(
                    select(Furniture).where(Furniture.category_name == category.name)
                )
                for item in items.scalars():
                    await session.delete(item)
                await session.flush()

                await session.delete(category)
                await session.commit()
                logger.info("Категория %s (ID %s) удалена", category.name, category_id)
                return True
            except SQLAlchemyError:
                await session.rollback()
                logger.exception("Ошибка при удалении категории с ID %s", category_id)
                return False


class CrudFurniture:
    def __init__(self):
        self.session = AsyncSessionLocal

    async def create_furniture(
        self,
        description: str,
        category: str,
        country: str,
        photos: Optional[list[str]] = None
    ) -> Optional[Furniture]:
        async with self.session() as session:
            try:
                photo_objects = [
                    FurniturePhoto(file_id=file_id)
                    for file_id in (photos or [])
                ]
                item = Furniture(
                    description=description,
                    category_name=category,
                    country_origin=country,
                    photos=photo_objects
                )
                session.add(item)
                await session.commit()
                await session.refresh(item, attribute_names=['photos'])
                return item
            except SQLAlchemyError:
                await session.rollback()
                logger.exception("Ошибка при создании мебели")
                return None

    async def add_photos_to_furniture(self, furniture_id: int, photos: list[str]) -> bool:
        if not photos:
            return True

        async with self.session() as session:
            try:
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

                stmt = stmt.order_by(Furniture.id)
                result = await session.execute(stmt)
                return list(result.scalars().all())
            except SQLAlchemyError:
                logger.exception("Ошибка при получении мебели для категории %s", category)
                return []

    async def get_all_furniture(self) -> list[Furniture]:
        async with self.session() as session:
            try:
                stmt = select(Furniture).options(selectinload(Furniture.photos))
                result = await session.execute(stmt)
                return list(result.scalars().all())
            except SQLAlchemyError:
                logger.exception("Ошибка при получении всей мебели")
                return []

    async def get_furniture_by_id(self, furniture_id: int) -> Optional[Furniture]:
        async with self.session() as session:
            try:
                stmt = (
                    select(Furniture)
                    .options(selectinload(Furniture.photos))
                    .where(Furniture.id == furniture_id)
                )
                result = await session.execute(stmt)
                return result.scalar_one_or_none()
            except SQLAlchemyError:
                logger.exception("Ошибка при получении мебели по ID %s", furniture_id)
                return None

    async def get_furniture_paginated(self, offset: int = 0, limit: int = 10) -> tuple[list[Furniture], int]:
        async with self.session() as session:
            try:
                count_stmt = select(func.count(Furniture.id))
                count_result = await session.execute(count_stmt)
                total = count_result.scalar_one() or 0

                stmt = (
                    select(Furniture)
                    .options(selectinload(Furniture.photos))
                    .order_by(Furniture.id.desc())
                    .offset(offset)
                    .limit(limit)
                )
                result = await session.execute(stmt)
                items = list(result.scalars().all())
                return items, total
            except SQLAlchemyError:
                logger.exception("Ошибка при получении пагинированного списка мебели")
                return [], 0

    async def delete_furniture(self, furniture_id: int) -> bool:
        async with self.session() as session:
            try:
                item = await session.get(Furniture, furniture_id)
                if not item:
                    logger.warning("Мебель с ID %s не найдена для удаления", furniture_id)
                    return False

                await session.delete(item)
                await session.commit()
                logger.info("Мебель с ID %s успешно удалена", furniture_id)
                return True

            except SQLAlchemyError:
                await session.rollback()
                logger.exception("Ошибка при удалении мебели с ID %s", furniture_id)
                return False

class CrudUser:
    def __init__(self):
        self.session = AsyncSessionLocal

    async def get_or_create_user(
        self,
        telegram_id: int,
        username: Optional[str] = None,
        firstname: Optional[str] = None,
        lastname: Optional[str] = None,
        is_admin: bool = False,
    ) -> Optional[User]:
        async with self.session() as session:
            try:
                stmt = select(User).where(User.telegram_id == telegram_id)
                result = await session.execute(stmt)
                user = result.scalar_one_or_none()

                if user:
                    if (
                        user.username != username
                        or user.firstname != firstname
                        or user.lastname != lastname
                        or user.is_admin != is_admin
                    ):
                        user.username = username
                        user.firstname = firstname
                        user.lastname = lastname
                        user.is_admin = is_admin
                        await session.commit()
                    return user

                new_user = User(
                    telegram_id=telegram_id,
                    username=username,
                    firstname=firstname,
                    lastname=lastname,
                    is_admin=is_admin,
                )
                session.add(new_user)
                await session.commit()
                await session.refresh(new_user)
                logger.info("Создан новый пользователь с telegram_id: %s", telegram_id)
                return new_user
            except IntegrityError:
                await session.rollback()
                stmt = select(User).where(User.telegram_id == telegram_id)
                result = await session.execute(stmt)
                return result.scalar_one_or_none()
            except SQLAlchemyError:
                await session.rollback()
                logger.exception("Ошибка при получении или создании пользователя %s", telegram_id)
                return None


class CrudCooperation:
    def __init__(self):
        self.session = AsyncSessionLocal

    async def create_request(
        self,
        name: str,
        phone: str,
        message: str | None = None,
    ) -> bool:
        async with self.session() as session:
            try:
                req = Cooperation(name=name, phone=phone, message=message)
                session.add(req)
                await session.commit()
                logger.info("Создана заявка на сотрудничество: %s", name)
                return True
            except SQLAlchemyError:
                await session.rollback()
                logger.exception("Ошибка при создании заявки")
                return False

    async def get_all_requests(self) -> list[Cooperation]:
        async with self.session() as session:
            try:
                stmt = select(Cooperation).order_by(Cooperation.created_at.desc())
                result = await session.execute(stmt)
                return list(result.scalars().all())
            except SQLAlchemyError:
                logger.exception("Ошибка при получении заявок")
                return []

    async def mark_processed(self, request_id: int) -> bool:
        async with self.session() as session:
            try:
                req = await session.get(Cooperation, request_id)
                if not req:
                    return False
                req.is_processed = True
                await session.commit()
                return True
            except SQLAlchemyError:
                await session.rollback()
                logger.exception("Ошибка при обновлении заявки")
                return False