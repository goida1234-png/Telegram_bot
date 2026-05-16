from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from data.questions import CHAPTERS


# ───────────── ГЛАВНОЕ МЕНЮ ─────────────

def main_menu_kb() -> InlineKeyboardMarkup:
    buttons = [
        [InlineKeyboardButton(text="🎮 Начать викторину", callback_data="menu_play")],
        [InlineKeyboardButton(text="📊 Моя статистика",  callback_data="menu_stats")],
        [InlineKeyboardButton(text="📁 Экспорт / Импорт", callback_data="menu_xml")],
        [InlineKeyboardButton(text="ℹ️ О боте",          callback_data="menu_about")],
    ]
    return InlineKeyboardMarkup(inline_keyboard=buttons)


# ───────────── ВЫБОР ГЛАВЫ ─────────────

def chapters_kb() -> InlineKeyboardMarkup:
    buttons = []

    for key, data in CHAPTERS.items():
        buttons.append([
            InlineKeyboardButton(
                text=f"{data['emoji']} {data['title']}",
                callback_data=f"chapter_{key}"
            )
        ])

    buttons.append([
        InlineKeyboardButton(text="🔙 Назад", callback_data="menu_back")
    ])

    return InlineKeyboardMarkup(inline_keyboard=buttons)


# ───────────── ВАРИАНТЫ ОТВЕТОВ ─────────────

def answers_kb(options: list[str], question_index: int) -> InlineKeyboardMarkup:
    """
    Генерирует кнопки вариантов ответа для текущего вопроса.
    callback_data формат: answer_{question_index}_{option_index}
    """
    buttons = []

    for i, option in enumerate(options):
        buttons.append([
            InlineKeyboardButton(
                text=option,
                callback_data=f"answer_{question_index}_{i}"
            )
        ])

    buttons.append([
        InlineKeyboardButton(text="🚪 Выйти из викторины", callback_data="quiz_exit")
    ])

    return InlineKeyboardMarkup(inline_keyboard=buttons)


# ───────────── ПОСЛЕ ОТВЕТА ─────────────

def next_question_kb(next_index: int) -> InlineKeyboardMarkup:
    """Кнопка перехода к следующему вопросу"""
    buttons = [
        [InlineKeyboardButton(
            text="➡️ Следующий вопрос",
            callback_data=f"next_{next_index}"
        )],
        [InlineKeyboardButton(text="🚪 Выйти из викторины", callback_data="quiz_exit")]
    ]
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def finish_kb() -> InlineKeyboardMarkup:
    """Кнопка после последнего вопроса"""
    buttons = [
        [InlineKeyboardButton(text="🏁 Посмотреть результат", callback_data="quiz_finish")]
    ]
    return InlineKeyboardMarkup(inline_keyboard=buttons)


# ───────────── ЭКРАН РЕЗУЛЬТАТА ─────────────

def result_kb(chapter_key: str) -> InlineKeyboardMarkup:
    """Кнопки после завершения викторины"""
    buttons = [
        [InlineKeyboardButton(text="🔄 Пройти ещё раз",  callback_data=f"chapter_{chapter_key}")],
        [InlineKeyboardButton(text="📚 Другая глава",    callback_data="menu_play")],
        [InlineKeyboardButton(text="🏠 Главное меню",    callback_data="menu_back")],
    ]
    return InlineKeyboardMarkup(inline_keyboard=buttons)


# ───────────── ПОДТВЕРЖДЕНИЕ ВЫХОДА ─────────────

def confirm_exit_kb() -> InlineKeyboardMarkup:
    """Диалог подтверждения выхода из викторины"""
    buttons = [
        [
            InlineKeyboardButton(text="✅ Да, выйти",      callback_data="exit_confirm"),
            InlineKeyboardButton(text="❌ Нет, продолжить", callback_data="exit_cancel"),
        ]
    ]
    return InlineKeyboardMarkup(inline_keyboard=buttons)


# ───────────── СТАТИСТИКА ─────────────

def stats_back_kb() -> InlineKeyboardMarkup:
    buttons = [
        [InlineKeyboardButton(text="🏠 Главное меню", callback_data="menu_back")]
    ]
    return InlineKeyboardMarkup(inline_keyboard=buttons)

# ───────────── XML ЭКСПОРТ / ИМПОРТ ─────────────

def xml_menu_kb() -> InlineKeyboardMarkup:
    buttons = [
        [InlineKeyboardButton(text="📤 Выгрузить результаты (XML)", callback_data="xml_export")],
        [InlineKeyboardButton(text="📥 Загрузить результаты (XML)", callback_data="xml_import")],
        [InlineKeyboardButton(text="🏠 Главное меню", callback_data="menu_back")],
    ]
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def xml_import_cancel_kb() -> InlineKeyboardMarkup:
    buttons = [
        [InlineKeyboardButton(text="❌ Отмена", callback_data="xml_import_cancel")]
    ]
    return InlineKeyboardMarkup(inline_keyboard=buttons)