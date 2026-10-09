from datetime import datetime
from uuid import uuid4
from sqlalchemy import Column, String, Integer, Boolean, DateTime, Text, ForeignKey
from sqlalchemy.orm import relationship
from database.engine import Base

# 1. ТАБЛИЦА ПОЛЬЗОВАТЕЛЕЙ
class User(Base):
    __tablename__ = 'users'

    # Уникальный текстовый ID в формате UUID (например: b561c9cd-d266-46ae...)
    id = Column(String(36), primary_key=True, default=lambda: str(uuid4()))
    telegram_id = Column(Integer, unique=True, nullable=False, index=True)
    username = Column(String, nullable=True)
    firstname = Column(String, nullable=True)
    lastname = Column(String, nullable=True)
    registration_date = Column(DateTime, default=lambda: datetime.now())
    is_admin = Column(Boolean, default=False, nullable=False) # Флаг: админ или клиент


# 2. ТАБЛИЦА КАТЕГОРИЙ МЕБЕЛИ
class Category(Base):
    __tablename__ = 'categories'

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False, unique=True) # Имя категории (Спальни, Кухни)
    description = Column(Text, nullable=True)          # Краткое описание
    created_at = Column(DateTime, default=lambda: datetime.now())

    def __repr__(self):
        return f"<Category(id={self.id}, name='{self.name}')>"


# 3. ТАБЛИЦА САМОЙ МЕБЕЛИ (ТОВАРОВ)
class Furniture(Base):
    __tablename__ = 'furniture'

    id = Column(Integer, primary_key=True, index=True)
    description = Column(Text, nullable=True)           # Размеры, обивка, цвет, цена
    category_name = Column(String, ForeignKey('categories.name'), nullable=False) # К какой категории относится
    country_origin = Column(String, nullable=True)      # Россия, Турция или форма кухни
    created_at = Column(DateTime, default=lambda: datetime.now())

    # Связка с таблицей фотографий: при удалении мебели удалятся и все её фото (delete-orphan)
    photos = relationship("FurniturePhoto", back_populates="furniture", cascade="all, delete-orphan")


# 4. ТАБЛИЦА ФОТОГРАФИЙ МЕБЕЛИ
class FurniturePhoto(Base):
    __tablename__ = 'furniture_photos'

    id = Column(Integer, primary_key=True, index=True)
    furniture_id = Column(Integer, ForeignKey('furniture.id'), nullable=False) # ID мебели
    file_id = Column(String, nullable=False)    # ТОТ САМЫЙ КЛЮЧ ФОТО В TELEGRAM!
    file_path = Column(String, nullable=True)   # Необязательный путь
    created_at = Column(DateTime, default=lambda: datetime.now())

    furniture = relationship("Furniture", back_populates="photos")