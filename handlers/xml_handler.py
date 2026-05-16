import io
import xml.etree.ElementTree as ET
from datetime import datetime

from aiogram import Router, F
from aiogram.types import (
    CallbackQuery, Message,
    BufferedInputFile, Document
)
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup

from database import get_all_sessions_for_export, import_session_from_xml
from keyboards import xml_menu_kb, xml_import_cancel_kb, main_menu_kb, xml_export_done_kb

router = Router()


# ───────────── FSM ─────────────

class XmlState(StatesGroup):
    waiting_for_file = State()


# ───────────── ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ ─────────────

def build_xml(data: dict) -> bytes:
    """Собирает XML из словаря данных пользователя"""
    user = data["user"]
    sessions = data["sessions"]

    root = ET.Element("quiz_results")
    root.set("exported_at", datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
    root.set("version", "1.0")

    # Блок пользователя
    user_el = ET.SubElement(root, "user")
    ET.SubElement(user_el, "tg_id").text      = str(user["tg_id"])
    ET.SubElement(user_el, "username").text   = user["username"] or ""
    ET.SubElement(user_el, "first_name").text = user["first_name"] or ""
    ET.SubElement(user_el, "joined_at").text  = str(user["joined_at"])

    # Блок сессий
    sessions_el = ET.SubElement(root, "sessions")
    sessions_el.set("total", str(len(sessions)))

    for item in sessions:
        s = item["session"]
        answers = item["answers"]

        session_el = ET.SubElement(sessions_el, "session")
        session_el.set("id",          str(s["id"]))
        session_el.set("chapter",     s["chapter"])
        session_el.set("score",       str(s["score"]))
        session_el.set("total",       str(s["total"]))
        session_el.set("started_at",  str(s["started_at"]))
        session_el.set("finished_at", str(s["finished_at"]))

        # Процент для удобства чтения
        pct = round((s["score"] / s["total"]) * 100) if s["total"] else 0
        session_el.set("percent", f"{pct}%")

        answers_el = ET.SubElement(session_el, "answers")

        for a in answers:
            answer_el = ET.SubElement(answers_el, "answer")
            answer_el.set("index",      str(a["question_index"]))
            answer_el.set("is_correct", str(a["is_correct"]))

            ET.SubElement(answer_el, "question").text = a["question_text"]
            ET.SubElement(answer_el, "chosen").text   = a["chosen_option"]
            ET.SubElement(answer_el, "correct").text  = a["correct_option"]

    # Красивое форматирование
    indent_xml(root)

    tree = ET.ElementTree(root)
    buffer = io.BytesIO()
    tree.write(buffer, encoding="utf-8", xml_declaration=True)
    return buffer.getvalue()


def indent_xml(elem, level=0):
    """Добавляет отступы для красивого XML"""
    indent = "\n" + "  " * level
    if len(elem):
        if not elem.text or not elem.text.strip():
            elem.text = indent + "  "
        if not elem.tail or not elem.tail.strip():
            elem.tail = indent
        for child in elem:
            indent_xml(child, level + 1)
        if not child.tail or not child.tail.strip():
            child.tail = indent
    else:
        if level and (not elem.tail or not elem.tail.strip()):
            elem.tail = indent


def parse_xml(content: bytes) -> list:
    """Парсит XML и возвращает список сессий для импорта"""
    root = ET.fromstring(content)
    sessions = []

    for session_el in root.findall(".//session"):
        answers = []
        for answer_el in session_el.findall(".//answer"):
            answers.append({
                "question_index": int(answer_el.get("index", 0)),
                "question_text":  answer_el.findtext("question", ""),
                "chosen_option":  answer_el.findtext("chosen", ""),
                "correct_option": answer_el.findtext("correct", ""),
                "is_correct":     int(answer_el.get("is_correct", 0)),
            })

        sessions.append({
            "chapter":     session_el.get("chapter", ""),
            "score":       int(session_el.get("score", 0)),
            "total":       int(session_el.get("total", 0)),
            "started_at":  session_el.get("started_at", ""),
            "finished_at": session_el.get("finished_at", ""),
            "answers":     answers,
        })

    return sessions


# ───────────── МЕНЮ XML ─────────────

@router.callback_query(F.data == "menu_xml")
async def show_xml_menu(callback: CallbackQuery):
    await callback.message.edit_text(
        text=(
            "📁 <b>Экспорт / Импорт результатов</b>\n\n"
            "📤 <b>Выгрузить</b> — скачать все твои результаты\n"
            "   в виде XML файла\n\n"
            "📥 <b>Загрузить</b> — восстановить результаты\n"
            "   из ранее сохранённого XML файла\n\n"
            "Выбери действие 👇"
        ),
        reply_markup=xml_menu_kb(),
        parse_mode="HTML"
    )
    await callback.answer()


# ───────────── ЭКСПОРТ ─────────────

@router.callback_query(F.data == "xml_export")
async def export_results(callback: CallbackQuery):
    await callback.answer("⏳ Формирую файл...")

    data = await get_all_sessions_for_export(callback.from_user.id)

    if not data or not data.get("sessions"):
        await callback.message.edit_text(
            text=(
                "📭 <b>Нет данных для экспорта</b>\n\n"
                "Ты ещё не завершил ни одной викторины.\n"
                "Пройди хотя бы одну главу — тогда появятся данные для выгрузки!"
            ),
            reply_markup=xml_menu_kb(),
            parse_mode="HTML"
        )
        return

    xml_bytes = build_xml(data)
    filename = f"quiz_results_{callback.from_user.id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xml"

    total_sessions = len(data["sessions"])
    total_answers  = sum(len(s["answers"]) for s in data["sessions"])

    # Отправляем файл
    await callback.message.answer_document(
        document=BufferedInputFile(xml_bytes, filename=filename),
        caption=(
            f"📤 <b>Экспорт завершён!</b>\n\n"
            f"📊 Сессий:  <b>{total_sessions}</b>\n"
            f"💬 Ответов: <b>{total_answers}</b>\n"
            f"📅 Дата:    <b>{datetime.now().strftime('%d.%m.%Y %H:%M')}</b>\n\n"
            f"💾 Сохрани файл — он понадобится для восстановления данных."
        ),
        reply_markup=xml_export_done_kb(),
        parse_mode="HTML"
    )

    await callback.message.delete()


# ───────────── ИМПОРТ ─────────────

@router.callback_query(F.data == "xml_import")
async def ask_for_xml_file(callback: CallbackQuery, state: FSMContext):
    await state.set_state(XmlState.waiting_for_file)

    # Удаляем текущее сообщение (оно с файлом — edit_text на нём не работает)
    try:
        await callback.message.delete()
    except Exception:
        pass

    # Отправляем новое сообщение
    await callback.message.answer(
        text=(
            "📥 <b>Загрузка результатов</b>\n\n"
            "Отправь XML файл, который был ранее\n"
            "выгружен из этого бота.\n\n"
            "⚠️ <i>Данные из файла добавятся к существующим,\n"
            "дубликаты не удаляются.</i>"
        ),
        reply_markup=xml_import_cancel_kb(),
        parse_mode="HTML"
    )
    await callback.answer()


@router.message(XmlState.waiting_for_file, F.document)
async def handle_xml_file(message: Message, state: FSMContext):
    document: Document = message.document

    # Проверяем расширение
    if not document.file_name.endswith(".xml"):
        await message.answer(
            text=(
                "❌ <b>Неверный формат файла</b>\n\n"
                "Нужен файл с расширением <b>.xml</b>\n"
                "Попробуй ещё раз или нажми Отмена."
            ),
            reply_markup=xml_import_cancel_kb(),
            parse_mode="HTML"
        )
        return

    # Скачиваем файл
    try:
        file = await message.bot.get_file(document.file_id)
        buffer = io.BytesIO()
        await message.bot.download_file(file.file_path, buffer)
        content = buffer.getvalue()
    except Exception:
        await message.answer(
            "❌ Не удалось скачать файл. Попробуй ещё раз.",
            reply_markup=xml_import_cancel_kb()
        )
        return

    # Парсим XML
    try:
        sessions = parse_xml(content)
    except ET.ParseError:
        await message.answer(
            text=(
                "❌ <b>Ошибка чтения XML</b>\n\n"
                "Файл повреждён или имеет неверный формат.\n"
                "Убедись что это файл из этого бота."
            ),
            reply_markup=xml_import_cancel_kb(),
            parse_mode="HTML"
        )
        return

    if not sessions:
        await message.answer(
            text=(
                "📭 <b>Файл пустой</b>\n\n"
                "В XML не найдено ни одной сессии."
            ),
            reply_markup=xml_import_cancel_kb(),
            parse_mode="HTML"
        )
        return

    # Импортируем сессии
    success_count = 0
    for s in sessions:
        ok = await import_session_from_xml(
            tg_id=message.from_user.id,
            username=message.from_user.username or "",
            first_name=message.from_user.first_name or "Игрок",
            chapter=s["chapter"],
            score=s["score"],
            total=s["total"],
            started_at=s["started_at"],
            finished_at=s["finished_at"],
            answers=s["answers"],
        )
        if ok:
            success_count += 1

    await state.clear()

    await message.answer(
        text=(
            f"✅ <b>Импорт завершён!</b>\n\n"
            f"📂 Загружено сессий: <b>{success_count}</b> из <b>{len(sessions)}</b>\n\n"
            f"Теперь они отображаются в твоей статистике 📊"
        ),
        reply_markup=main_menu_kb(),
        parse_mode="HTML"
    )


@router.message(XmlState.waiting_for_file)
async def handle_wrong_input(message: Message):
    """Пользователь прислал не файл"""
    await message.answer(
        text=(
            "❌ Нужен XML файл, а не текст или фото.\n\n"
            "Прикрепи файл через скрепку 📎"
        ),
        reply_markup=xml_import_cancel_kb(),
        parse_mode="HTML"
    )


@router.callback_query(F.data == "xml_import_cancel")
async def cancel_import(callback: CallbackQuery, state: FSMContext):
    await state.clear()
    await callback.message.edit_text(
        text=(
            "📁 <b>Экспорт / Импорт результатов</b>\n\n"
            "Выбери действие 👇"
        ),
        reply_markup=xml_menu_kb(),
        parse_mode="HTML"
    )
    await callback.answer("❌ Отменено")