import random
from aiogram import Router, F
from aiogram.types import CallbackQuery
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup

from data.questions import CHAPTERS
from database import (
    get_or_create_user,
    create_session,
    finish_session,
    save_answer
)
from keyboards import (
    answers_kb,
    next_question_kb,
    finish_kb,
    result_kb,
    confirm_exit_kb,
    chapters_kb
)

router = Router()


# ───────────── FSM СОСТОЯНИЯ ─────────────

class QuizState(StatesGroup):
    in_progress = State()


# ───────────── ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ ─────────────

def build_question_text(
    chapter_title: str,
    question_data: dict,
    index: int,
    total: int
) -> str:
    """Формирует красивый текст вопроса"""
    progress_bar = build_progress_bar(index, total)

    return (
        f"📚 <b>{chapter_title}</b>\n"
        f"{progress_bar}\n"
        f"❓ Вопрос <b>{index + 1}</b> из <b>{total}</b>\n\n"
        f"<b>{question_data['question']}</b>\n\n"
        f"Выбери ответ 👇"
    )


def build_progress_bar(current: int, total: int) -> str:
    """Рисует прогресс-бар из эмодзи"""
    filled = round((current / total) * 10)
    empty = 10 - filled
    return f"[{'🟩' * filled}{'⬜' * empty}] {current}/{total}"


def build_result_text(
    chapter_title: str,
    score: int,
    total: int,
    wrong_answers: list
) -> str:
    """Формирует экран результата"""
    percent = round((score / total) * 100)

    # Оценка результата
    if percent == 100:
        grade = "🏆 Абсолютный результат! Ты эксперт!"
    elif percent >= 80:
        grade = "🥇 Отличный результат! Так держать!"
    elif percent >= 60:
        grade = "🥈 Хороший результат! Есть куда расти."
    elif percent >= 40:
        grade = "🥉 Неплохо, но стоит повторить тему."
    else:
        grade = "😅 Попробуй ещё раз — всё получится!"

    # Звёзды
    stars = round((score / total) * 5)
    stars_str = "⭐" * stars + "☆" * (5 - stars)

    text = (
        f"🏁 <b>Викторина завершена!</b>\n"
        f"📚 Тема: <b>{chapter_title}</b>\n\n"
        f"━━━━━━━━━━━━━━━\n"
        f"✅ Правильных:  <b>{score}</b>\n"
        f"❌ Неверных:    <b>{total - score}</b>\n"
        f"📊 Результат:   <b>{percent}%</b>\n"
        f"🌟 Оценка:      {stars_str}\n"
        f"━━━━━━━━━━━━━━━\n\n"
        f"{grade}\n"
    )

    # Разбор ошибок (максимум 5 штук чтобы не перегружать)
    if wrong_answers:
        text += f"\n📝 <b>Твои ошибки:</b>\n"
        for i, item in enumerate(wrong_answers[:5], 1):
            text += (
                f"\n{i}. {item['question']}\n"
                f"   ❌ Твой ответ: <i>{item['chosen']}</i>\n"
                f"   ✅ Верный ответ: <i>{item['correct']}</i>\n"
            )
        if len(wrong_answers) > 5:
            text += f"\n...и ещё {len(wrong_answers) - 5} ошибок\n"

    return text


# ───────────── НАЧАЛО ГЛАВЫ ─────────────

@router.callback_query(F.data.startswith("chapter_"))
async def start_chapter(callback: CallbackQuery, state: FSMContext):
    chapter_key = callback.data.split("_", 1)[1]

    if chapter_key not in CHAPTERS:
        await callback.answer("❌ Глава не найдена!", show_alert=True)
        return

    chapter = CHAPTERS[chapter_key]
    questions = chapter["questions"].copy()
    random.shuffle(questions)  # Перемешиваем вопросы каждый раз

    # Создаём сессию в БД
    user_id = await get_or_create_user(
        tg_id=callback.from_user.id,
        username=callback.from_user.username or "",
        first_name=callback.from_user.first_name or "Игрок"
    )
    session_id = await create_session(
        user_id=user_id,
        chapter=chapter_key,
        total=len(questions)
    )

    # Сохраняем состояние в FSM
    await state.set_state(QuizState.in_progress)
    await state.set_data({
        "chapter_key":   chapter_key,
        "chapter_title": chapter["title"],
        "questions":     questions,
        "current":       0,
        "score":         0,
        "session_id":    session_id,
        "wrong_answers": [],
    })

    # Показываем первый вопрос
    question = questions[0]
    await callback.message.edit_text(
        text=build_question_text(chapter["title"], question, 0, len(questions)),
        reply_markup=answers_kb(question["options"], 0),
        parse_mode="HTML"
    )
    await callback.answer()


# ───────────── ОБРАБОТКА ОТВЕТА ─────────────

@router.callback_query(QuizState.in_progress, F.data.startswith("answer_"))
async def handle_answer(callback: CallbackQuery, state: FSMContext):
    data = await state.get_data()

    # Парсим callback: answer_{question_index}_{option_index}
    parts = callback.data.split("_")
    question_index = int(parts[1])
    option_index   = int(parts[2])

    # Защита от двойного нажатия
    if question_index != data["current"]:
        await callback.answer("⚠️ Этот вопрос уже отвечен!", show_alert=True)
        return

    questions     = data["questions"]
    question_data = questions[question_index]
    chosen_option = question_data["options"][option_index]
    correct_option = question_data["answer"]
    is_correct    = (chosen_option == correct_option)

    # Обновляем счёт и список ошибок
    score         = data["score"] + (1 if is_correct else 0)
    wrong_answers = data["wrong_answers"]

    if not is_correct:
        wrong_answers.append({
            "question": question_data["question"],
            "chosen":   chosen_option,
            "correct":  correct_option,
        })

    # Сохраняем ответ в БД
    await save_answer(
        session_id=data["session_id"],
        question_index=question_index,
        question_text=question_data["question"],
        chosen_option=chosen_option,
        correct_option=correct_option,
        is_correct=is_correct
    )

    # Обновляем FSM
    await state.update_data(
        score=score,
        wrong_answers=wrong_answers
    )

    total       = len(questions)
    is_last     = (question_index == total - 1)
    next_index  = question_index + 1

    # Текст реакции на ответ
    if is_correct:
        reaction = "✅ <b>Правильно!</b> 🎉"
    else:
        reaction = (
            f"❌ <b>Неверно!</b>\n"
            f"Правильный ответ: <i>{correct_option}</i>"
        )

    progress_bar = build_progress_bar(next_index, total)

    result_text = (
        f"📚 <b>{data['chapter_title']}</b>\n"
        f"{progress_bar}\n\n"
        f"{reaction}\n\n"
        f"🏆 Счёт: <b>{score}/{next_index}</b>"
    )

    if is_last:
        await callback.message.edit_text(
            text=result_text,
            reply_markup=finish_kb(),
            parse_mode="HTML"
        )
    else:
        await callback.message.edit_text(
            text=result_text,
            reply_markup=next_question_kb(next_index),
            parse_mode="HTML"
        )

    await callback.answer("✅ Верно!" if is_correct else "❌ Неверно!")


# ───────────── СЛЕДУЮЩИЙ ВОПРОС ─────────────

@router.callback_query(QuizState.in_progress, F.data.startswith("next_"))
async def next_question(callback: CallbackQuery, state: FSMContext):
    data  = await state.get_data()
    index = int(callback.data.split("_")[1])

    await state.update_data(current=index)

    questions     = data["questions"]
    question_data = questions[index]
    total         = len(questions)

    await callback.message.edit_text(
        text=build_question_text(data["chapter_title"], question_data, index, total),
        reply_markup=answers_kb(question_data["options"], index),
        parse_mode="HTML"
    )
    await callback.answer()


# ───────────── ФИНИШ ─────────────

@router.callback_query(QuizState.in_progress, F.data == "quiz_finish")
async def show_result(callback: CallbackQuery, state: FSMContext):
    data = await state.get_data()

    # Записываем финальный счёт в БД
    await finish_session(
        session_id=data["session_id"],
        score=data["score"]
    )

    await callback.message.edit_text(
        text=build_result_text(
            chapter_title=data["chapter_title"],
            score=data["score"],
            total=len(data["questions"]),
            wrong_answers=data["wrong_answers"]
        ),
        reply_markup=result_kb(data["chapter_key"]),
        parse_mode="HTML"
    )

    await state.clear()
    await callback.answer()


# ───────────── ВЫХОД ИЗ ВИКТОРИНЫ ─────────────

@router.callback_query(QuizState.in_progress, F.data == "quiz_exit")
async def ask_exit(callback: CallbackQuery):
    await callback.message.edit_text(
        text=(
            "⚠️ <b>Выйти из викторины?</b>\n\n"
            "😔 Прогресс текущей игры не сохранится.\n"
            "Ты уверен?"
        ),
        reply_markup=confirm_exit_kb(),
        parse_mode="HTML"
    )
    await callback.answer()


@router.callback_query(QuizState.in_progress, F.data == "exit_confirm")
async def confirm_exit(callback: CallbackQuery, state: FSMContext):
    await state.clear()
    await callback.message.edit_text(
        text=(
            "🏠 <b>Главное меню</b>\n\n"
            "Ты вышел из викторины.\n"
            "Выбери действие 👇"
        ),
        reply_markup=__import__("keyboards").main_menu_kb(),
        parse_mode="HTML"
    )
    await callback.answer()


@router.callback_query(QuizState.in_progress, F.data == "exit_cancel")
async def cancel_exit(callback: CallbackQuery, state: FSMContext):
    """Возврат к текущему вопросу"""
    data  = await state.get_data()
    index = data["current"]

    questions     = data["questions"]
    question_data = questions[index]
    total         = len(questions)

    await callback.message.edit_text(
        text=build_question_text(data["chapter_title"], question_data, index, total),
        reply_markup=answers_kb(question_data["options"], index),
        parse_mode="HTML"
    )
    await callback.answer("▶️ Продолжаем!")