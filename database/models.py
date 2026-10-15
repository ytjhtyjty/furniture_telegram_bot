from datetime import datetime, timezone
from uuid import uuid4
from sqlalchemy import Column, String, Integer, BigInteger, Boolean, DateTime, Text, ForeignKey
from sqlalchemy.orm import relationship
from database.engine import Base


class User(Base):
    __tablename__ = 'users'

    id = Column(String(36), primary_key=True, default=lambda: str(uuid4()))
    telegram_id = Column(BigInteger, unique=True, nullable=False, index=True)
    username = Column(String, nullable=True)
    firstname = Column(String, nullable=True)
    lastname = Column(String, nullable=True)
    registration_date = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    is_admin = Column(Boolean, default=False, nullable=False) # Флаг: админ или клиент


class Category(Base):
    __tablename__ = 'categories'

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False, unique=True)
    description = Column(Text, nullable=True)
    furniture_type = Column(String, nullable=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    def __repr__(self):
        return f"<Category(id={self.id}, name='{self.name}')>"


class Furniture(Base):
    __tablename__ = 'furniture'

    id = Column(Integer, primary_key=True, index=True)
    description = Column(Text, nullable=True)
    category_name = Column(String, ForeignKey('categories.name'), nullable=False)
    country_origin = Column(String, nullable=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    photos = relationship("FurniturePhoto", back_populates="furniture", cascade="all, delete-orphan", lazy="selectin")


class FurniturePhoto(Base):
    __tablename__ = 'furniture_photos'

    id = Column(Integer, primary_key=True, index=True)
    furniture_id = Column(Integer, ForeignKey('furniture.id'), nullable=False)
    file_id = Column(String, nullable=False)
    file_path = Column(String, nullable=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    furniture = relationship("Furniture", back_populates="photos")


class Cooperation(Base):
    __tablename__ = 'cooperations'

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)
    phone = Column(String, nullable=False)
    message = Column(Text, nullable=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    is_processed = Column(Boolean, default=False)

