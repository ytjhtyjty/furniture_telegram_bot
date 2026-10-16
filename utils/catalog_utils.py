COUNTRY_BY_CB = {
    "russian_origin": "Россия",
    "turkey_origin": "Турция",
}
KITCHEN_TYPE_BY_CB = {
    "straight_kitchen": "Прямая кухня",
    "corner_kitchen": "Угловая кухня",
}

KITCHEN_COUNTRY = "Россия"

# Режимы подкатегорий
MODE_KITCHEN = "kitchen"
MODE_COUNTRY = "country"
MODE_DIRECT = "direct"

MODE_BY_FURNITURE_TYPE = {
    "sleep_furniture": MODE_COUNTRY,
    "kitchen_furniture": MODE_KITCHEN,
    "soft_furniture": MODE_COUNTRY,
    "tables_chairs": MODE_COUNTRY,
    "cabinets_commodes": MODE_DIRECT,
    "bed_furniture": MODE_DIRECT,
    "mattresses": MODE_DIRECT,
    "wardrobes": MODE_DIRECT,
}

CATEGORY_NAME_MAX = 50
CATEGORY_DESCRIPTION_MAX = 200
FURNITURE_DESCRIPTION_MAX = 700
MAX_PHOTOS = 10


def _mode_by_name(name: str | None) -> str:
    n = (name or "").lower()
    if "кухон" in n or "кухн" in n:
        return MODE_KITCHEN
    if any(part in n for part in ("спальн", "мягк", "стол")):
        return MODE_COUNTRY
    return MODE_DIRECT


def get_category_mode(category) -> str:
    furniture_type = getattr(category, "furniture_type", None)
    if furniture_type in MODE_BY_FURNITURE_TYPE:
        return MODE_BY_FURNITURE_TYPE[furniture_type]
    return _mode_by_name(getattr(category, "name", None))


def split_kitchen_prefix(description: str | None) -> tuple[str | None, str]:
    text = description or ""
    for kitchen_type in KITCHEN_TYPE_BY_CB.values():
        prefix = f"[{kitchen_type}]"
        if text.startswith(prefix):
            return kitchen_type, text[len(prefix):].lstrip()
    return None, text


from keyboard.button_template import furniture_types_kb  # noqa: E402

FURNITURE_TYPE_TITLES: dict[str, str] = {cb: text for text, cb in furniture_types_kb}


def parse_id_and_page(data: str) -> tuple[int, int] | None:
    """Разбирает callback_data вида 'prefix:id:page' и возвращает (id, page)."""
    parts = data.split(":")
    if len(parts) != 3:
        return None
    try:
        return int(parts[1]), int(parts[2])
    except ValueError:
        return None
