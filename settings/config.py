import os
from dotenv import load_dotenv

 
# Загружаем переменные из секретного файла .env
load_dotenv()
 
def _parse_admin_ids(raw: str) -> list[int]:
    ids = []
    for part in raw.split(","):
        part = part.strip()
        if part.isdigit():
            ids.append(int(part))
    return ids


class ConfigBot:
    TOKEN = os.getenv("BOT_TOKEN", "").strip()
 
    ADMIN_IDS = _parse_admin_ids(os.getenv("ADMIN_IDS", ""))