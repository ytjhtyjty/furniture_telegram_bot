import os
from dotenv import load_dotenv


load_dotenv()


def _parse_admin_ids(raw: str) -> list[int]:
    ids = []
    for part in raw.split(","):
        part = part.strip()
        try:
            ids.append(int(part))
        except ValueError:
            continue
    return ids


class ConfigBot:
    TOKEN = os.getenv("BOT_TOKEN", "").strip()

    ADMIN_IDS = _parse_admin_ids(os.getenv("ADMIN_IDS", ""))

    CONTACT_PHONE = os.getenv("CONTACT_PHONE", "").strip()
    CONTACT_WHATSAPP = os.getenv("CONTACT_WHATSAPP", "").strip()
    CONTACT_TELEGRAM = os.getenv("CONTACT_TELEGRAM", "").strip()
    CONTACT_INSTAGRAM = os.getenv("CONTACT_INSTAGRAM", "").strip()
