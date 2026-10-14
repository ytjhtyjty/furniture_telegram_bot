import atexit
import logging
import os
import sys
from datetime import datetime

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
LOG_DIR = os.getenv("LOG_DIR") or os.path.join(BASE_DIR, "logs")
LOG_FILE = os.path.join(LOG_DIR, "logs.txt")

LOG_FORMAT = "%(asctime)s - %(levelname)s - %(name)s - %(message)s"

_file_handler: logging.FileHandler | None = None


def _unique_archive_path(day: str) -> str:
    path = os.path.join(LOG_DIR, f"{day}_logs.txt")
    counter = 2
    while os.path.exists(path):
        path = os.path.join(LOG_DIR, f"{day}_logs_{counter}.txt")
        counter += 1
    return path


def _archive_current_log(when: datetime | None = None) -> str | None:
    if not os.path.exists(LOG_FILE):
        return None
    if os.path.getsize(LOG_FILE) == 0:
        os.remove(LOG_FILE)
        return None
    when = when or datetime.now()
    target = _unique_archive_path(when.strftime("%Y-%m-%d"))
    os.replace(LOG_FILE, target)
    return target


def setup_logging(level: int = logging.INFO) -> None:
    global _file_handler
    os.makedirs(LOG_DIR, exist_ok=True)

    leftover = None
    if os.path.exists(LOG_FILE):
        leftover = _archive_current_log(datetime.fromtimestamp(os.path.getmtime(LOG_FILE)))

    formatter = logging.Formatter(LOG_FORMAT)

    console = logging.StreamHandler(sys.stderr)
    console.setFormatter(formatter)

    _file_handler = logging.FileHandler(LOG_FILE, mode="w", encoding="utf-8")
    _file_handler.setFormatter(formatter)

    root = logging.getLogger()
    root.setLevel(level)
    root.handlers.clear()
    root.addHandler(console)
    root.addHandler(_file_handler)


    logging.getLogger("aiosqlite").setLevel(logging.WARNING)
    logging.getLogger("sqlalchemy.engine").setLevel(logging.WARNING)

    logging.info("=" * 60)
    logging.info("Запуск бота. Лог пишется в %s", LOG_FILE)
    if leftover:
        logging.warning("Предыдущий запуск завершился аварийно, его лог сохранён: %s",
                        os.path.basename(leftover))


    atexit.register(shutdown_logging)


def shutdown_logging() -> None:
    global _file_handler
    if _file_handler is None:
        return

    logging.info("Остановка бота. Лог будет сохранён как ГГГГ-ММ-ДД_logs.txt")

    handler, _file_handler = _file_handler, None
    logging.getLogger().removeHandler(handler)
    handler.close()

    archived = _archive_current_log()
    if archived:
        print(f"Лог сохранён: {archived}", file=sys.stderr)
