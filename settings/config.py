import os
from dotenv import load_dotenv
 
# Загружаем переменные из секретного файла .env
load_dotenv()
 
 
class ConfigBot:
    TOKEN = os.getenv("BOT_TOKEN", "")
 
    ADMIN_IDS = [
        int(x) for x in os.getenv("ADMIN_IDS", "").replace(" ", "").split(",") if x
    ]