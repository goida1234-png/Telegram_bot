from aiogram import Router, F
from aiogram.types import CallbackQuery

from database import get_user_stats
from keyboards import main_menu_kb, chapters_kb, stats_back_kb

router = Router()


# ───────────── ГЛАВНОЕ МЕНЮ ─────────────

@router.callback_query(F.data == "menu_back")
async def show_main_menu(callback: CallbackQuery):
    await callback.message.edit_text(
        text=(
            "🏠 <b>Главное меню</b>\n\n"
            "Выбери действие 👇"
        ),
        reply_markup=main_menu_kb(),
        parse_mode="HTML"
    )
    await callback.answer()


# ───────────── ВЫБОР ГЛАВЫ ─────────────

@router.callback_query(F.data == "menu_play")
async def show_chapters(callback: CallbackQuery):
    await callback.message.edit_text(
        text=(
            "📚 <b>Выбор главы</b>\n\n"
            "🎯 В каждой главе <b>20 вопросов</b>\n"
            "⏱ Отвечай внимательно — результат сохранится!\n\n"
            "Выбери тему 👇"
        ),
        reply_markup=chapters_kb(),
        parse_mode="HTML"
    )
    await callback.answer()


# ───────────── СТАТИСТИКА ─────────────

@router.callback_query(F.data == "menu_stats")
async def show_stats(callback: CallbackQuery):
    stats = await get_user_stats(callback.from_user.id)

    if not stats:
        text = (
            "📊 <b>Твоя статистика</b>\n\n"
            "😅 Ты ещё не прошёл ни одной викторины.\n"
            "Нажми <b>Начать викторину</b> и сыграй первый раз!"
        )
    else:
        lines = ["📊 <b>Твоя статистика</b>\n"]

        medals = ["🥇", "🥈", "🥉"]
        chapter_emojis = {
            "dota2":    "🎮",
            "csgo":     "🔫",
            "football": "⚽",
            "general":  "🧠",
        }

        for i, (chapter, data) in enumerate(stats.items()):
            medal = medals[i] if i < len(medals) else "🏅"
            emoji = chapter_emojis.get(chapter, "📌")

            # Звёздочный рейтинг из 5
            stars = round((data["best"] / 20) * 5)
            stars_str = "⭐" * stars + "☆" * (5 - stars)

            lines.append(
                f"{medal} {emoji} <b>{chapter.upper()}</b>\n"
                f"   🎮 Игр сыграно:  <b>{data['games']}</b>\n"
                f"   🏆 Лучший счёт:  <b>{data['best']}/20</b>\n"
                f"   📈 Средний %:    <b>{data['avg_pct']}%</b>\n"
                f"   {stars_str}\n"
            )

        text = "\n".join(lines)

    await callback.message.edit_text(
        text=text,
        reply_markup=stats_back_kb(),
        parse_mode="HTML"
    )
    await callback.answer()


# ───────────── О БОТЕ ─────────────

@router.callback_query(F.data == "menu_about")
async def show_about(callback: CallbackQuery):
    await callback.message.edit_text(
        text=(
            "ℹ️ <b>О боте</b>\n\n"
            "🤖 <b>Викторина-бот</b> — проверь свои знания!\n\n"
            "📚 <b>Доступные главы:</b>\n"
            "   🎮 Dota 2 — 20 вопросов\n"
            "   🔫 CS2 / CS:GO — 20 вопросов\n"
            "   ⚽ Футбол — 20 вопросов\n"
            "   🧠 Общие знания — 20 вопросов\n\n"
            "💾 <b>Все ответы</b> сохраняются в базу данных\n"
            "📊 <b>Статистика</b> доступна в главном меню\n"
            "🔄 <b>Можно перепроходить</b> главы сколько угодно\n\n"
            "🏆 Удачи в викторине!"
        ),
        reply_markup=main_menu_kb(),
        parse_mode="HTML"
    )
    await callback.answer()