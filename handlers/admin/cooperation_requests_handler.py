from html import escape

from aiogram import Router, F, types

from database.crud import CrudCooperation
from keyboard.keyboard_builder import make_row_inline_keyboards
from utils.messages import safe_edit_text

router = Router()

PAGE_SIZE = 5
MESSAGE_PREVIEW_LEN = 300


async def _render_requests_page(callback: types.CallbackQuery, page: int = 0) -> None:
    requests = await CrudCooperation().get_all_requests()

    if not requests:
        await safe_edit_text(
            callback.message,
            "📭 Заявок на сотрудничество пока нет.",
            make_row_inline_keyboards([("⬅️ Назад", "settings_bot")]),
        )
        return

    total_pages = (len(requests) + PAGE_SIZE - 1) // PAGE_SIZE
    page = max(0, min(page, total_pages - 1))
    page_items = requests[page * PAGE_SIZE:(page + 1) * PAGE_SIZE]
    new_count = sum(1 for r in requests if not r.is_processed)

    lines = [f"🤝 <b>Заявки на сотрудничество</b> (всего: {len(requests)}, новых: {new_count})\n"]
    buttons = []
    for r in page_items:
        status = "✅" if r.is_processed else "🔵"
        lines.append(
            f"{status} <b>#{r.id}. {escape(r.name or '—')}</b>\n"
            f"   📞 {escape(r.phone or '—')}\n"
            f"   📝 {escape((r.message or '—')[:MESSAGE_PREVIEW_LEN])}\n"
            f"   🕐 {r.created_at.strftime('%d.%m.%Y %H:%M') if r.created_at else '—'}\n"
        )
        if not r.is_processed:
            buttons.append((f"✅ Отметить #{r.id} обработанной", f"coop_done:{r.id}:{page}"))

    if page > 0:
        buttons.append(("◀️ Назад", f"coop_page:{page - 1}"))
    if total_pages > 1:
        buttons.append((f"Стр. {page + 1}/{total_pages}", "noop_page"))
    if page < total_pages - 1:
        buttons.append(("Вперёд ▶️", f"coop_page:{page + 1}"))
    buttons.append(("⬅️ В админ-панель", "settings_bot"))

    await safe_edit_text(callback.message, "\n".join(lines), make_row_inline_keyboards(buttons))


@router.callback_query(F.data == "cooperation_requests")
async def show_requests(callback: types.CallbackQuery):
    await callback.answer()
    await _render_requests_page(callback, page=0)


@router.callback_query(F.data.startswith("coop_page:"))
async def change_requests_page(callback: types.CallbackQuery):
    await callback.answer()
    try:
        page = int(callback.data.split(":")[1])
    except (ValueError, IndexError):
        page = 0
    await _render_requests_page(callback, page=page)


@router.callback_query(F.data.startswith("coop_done:"))
async def mark_request_processed(callback: types.CallbackQuery):
    parts = callback.data.split(":")
    try:
        request_id, page = int(parts[1]), int(parts[2])
    except (ValueError, IndexError):
        await callback.answer()
        return

    if await CrudCooperation().mark_processed(request_id):
        await callback.answer(f"✅ Заявка #{request_id} обработана")
    else:
        await callback.answer("⚠️ Заявка не найдена", show_alert=True)
    await _render_requests_page(callback, page=page)
