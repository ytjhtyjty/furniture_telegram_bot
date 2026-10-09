import os
from sqlalchemy.orm import DeclarativeBase
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncAttrs

# Вычисляем точный путь к папке проекта на любом компьютере
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
# Файл базы будет лежать в папке database/database.db
DB_PATH = os.path.join(BASE_DIR, 'database', 'database.db')

# Формируем специальную строку подключения для асинхронного SQLite
DATABASE_URL = f'sqlite+aiosqlite:///{DB_PATH}'

# Создаем асинхронный движок (echo=False чтобы консоль не засорялась логами SQL)
async_engine = create_async_engine(DATABASE_URL, echo=False, pool_size=10)

# Фабрика сессий (каждый запрос к базе будет открывать и закрывать свою чистую сессию)
AsyncSessionLocal = async_sessionmaker(bind=async_engine, expire_on_commit=False)

# Главный родительский класс для всех таблиц
class Base(AsyncAttrs, DeclarativeBase):
    pass

