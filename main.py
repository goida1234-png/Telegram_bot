import asyncio
import json
import random
import os
from datetime import datetime
from typing import Dict, List, Optional

from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command, CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.types import (
    InlineKeyboardMarkup, InlineKeyboardButton,
    ReplyKeyboardMarkup, KeyboardButton,
    CallbackQuery
)

# Конфигурация
BOT_TOKEN = "YOUR_BOT_TOKEN_HERE"  # Замените на ваш токен

# Инициализация бота и диспетчера
bot = Bot(token=BOT_TOKEN)
storage = MemoryStorage()
dp = Dispatcher(storage=storage)


# Класс для хранения данных пользователя
class UserData:
    def __init__(self, user_id: int, username: str = ""):
        self.user_id = user_id
        self.username = username
        self.total_score = 0
        self.games_played = 0
        self.correct_answers = 0
        self.total_answers = 0
        self.current_game = None

    def to_dict(self):
        return {
            "user_id": self.user_id,
            "username": self.username,
            "total_score": self.total_score,
            "games_played": self.games_played,
            "correct_answers": self.correct_answers,
            "total_answers": self.total_answers
        }


# Класс для состояния игры
class GameState:
    def __init__(self, category: str, questions: List[Dict]):
        self.category = category
        self.questions = questions
        self.current_index = 0
        self.score = 0
        self.answers = []
        self.start_time = datetime.now()

    def get_current_question(self) -> Optional[Dict]:
        if self.current_index < len(self.questions):
            return self.questions[self.current_index]
        return None

    def is_finished(self) -> bool:
        return self.current_index >= len(self.questions)


# База данных вопросов
QUESTIONS = {
    "history": [
        {
            "question": "В каком году началась Вторая мировая война?",
            "options": ["1939", "1941", "1937", "1945"],
            "correct": 0,
            "explanation": "Вторая мировая война началась 1 сентября 1939 года с вторжения Германии в Польшу."
        },
        {
            "question": "Кто был первым президентом США?",
            "options": ["Томас Джефферсон", "Джордж Вашингтон", "Авраам Линкольн", "Джон Адамс"],
            "correct": 1,
            "explanation": "Джордж Вашингтон был первым президентом США (1789-1797)."
        },
        {
            "question": "В каком году был основан Рим?",
            "options": ["753 г. до н.э.", "476 г. н.э.", "27 г. до н.э.", "313 г. н.э."],
            "correct": 0,
            "explanation": "Согласно легенде, Рим был основан Ромулом и Ремом в 753 году до н.э."
        }
    ],
    "science": [
        {
            "question": "Какая планета самая большая в Солнечной системе?",
            "options": ["Сатурн", "Юпитер", "Нептун", "Уран"],
            "correct": 1,
            "explanation": "Юпитер - самая большая планета, её масса в 2.5 раза больше массы всех остальных планет вместе взятых."
        },
        {
            "question": "Из чего состоит вода?",
            "options": ["Кислород и водород", "Водород и гелий", "Кислород и азот", "Углерод и кислород"],
            "correct": 0,
            "explanation": "Вода (H2O) состоит из двух атомов водорода и одного атома кислорода."
        },
        {
            "question": "Какая самая высокая гора в мире?",
            "options": ["К2", "Эверест", "Канченджанга", "Лхоцзе"],
            "correct": 1,
            "explanation": "Эверест (Джомолунгма) высотой 8848 метров над уровнем моря."
        }
    ],
    "geography": [
        {
            "question": "Какая самая длинная река в мире?",
            "options": ["Амазонка", "Нил", "Янцзы", "Миссисипи"],
            "correct": 0,
            "explanation": "Амазонка считается самой длинной рекой в мире (около 7000 км)."
        },
        {
            "question": "Столица Франции?",
            "options": ["Лион", "Марсель", "Париж", "Бордо"],
            "correct": 2,
            "explanation": "Париж - столица и крупнейший город Франции."
        },
        {
            "question": "Какая пустыня самая большая в мире?",
            "options": ["Гоби", "Калахари", "Сахара", "Атакама"],
            "correct": 2,
            "explanation": "Сахара - крупнейшая жаркая пустыня, покрывающая большую часть Северной Африки."
        }
    ]
}


# Состояния FSM
class QuizStates(StatesGroup):
    choosing_category = State()
    playing = State()
    waiting_for_next = State()


# Хранилище данных пользователей
user_data: Dict[int, UserData] = {}
data_file = "user_data.json"


# Загрузка данных пользователей
def load_user_data():
    global user_data
    if os.path.exists(data_file):
        try:
            with open(data_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
                for user_id, user_info in data.items():
                    user = UserData(user_info['user_id'], user_info.get('username', ''))
                    user.total_score = user_info['total_score']
                    user.games_played = user_info['games_played']
                    user.correct_answers = user_info['correct_answers']
                    user.total_answers = user_info['total_answers']
                    user_data[int(user_id)] = user
        except Exception as e:
            print(f"Ошибка загрузки данных: {e}")


# Сохранение данных пользователей
def save_user_data():
    try:
        with open(data_file, 'w', encoding='utf-8') as f:
            data = {str(uid): user.to_dict() for uid, user in user_data.items()}
            json.dump(data, f, ensure_ascii=False, indent=2)
    except Exception as e:
        print(f"Ошибка сохранения данных: {e}")


# Получение или создание пользователя
def get_user(user_id: int, username: str = "") -> UserData:
    if user_id not in user_data:
        user_data[user_id] = UserData(user_id, username)
    elif username and user_data[user_id].username != username:
        user_data[user_id].username = username
    return user_data[user_id]


# Создание клавиатуры с категориями
def get_categories_keyboard() -> InlineKeyboardMarkup:
    buttons = [
        [InlineKeyboardButton(text="📜 История", callback_data="cat_history")],
        [InlineKeyboardButton(text="🔬 Наука", callback_data="cat_science")],
        [InlineKeyboardButton(text="🌍 География", callback_data="cat_geography")],
        [InlineKeyboardButton(text="🎲 Случайная категория", callback_data="cat_random")]
    ]
    return InlineKeyboardMarkup(inline_keyboard=buttons)


# Создание клавиатуры для ответов
def get_answers_keyboard(options: List[str], question_index: int) -> InlineKeyboardMarkup:
    buttons = []
    for i, option in enumerate(options):
        buttons.append([InlineKeyboardButton(
            text=f"{chr(65 + i)}. {option}",  # A, B, C, D
            callback_data=f"answer_{question_index}_{i}"
        )])
    return InlineKeyboardMarkup(inline_keyboard=buttons)


# Главное меню
@dp.message(CommandStart())
async def cmd_start(message: types.Message, state: FSMContext):
    user = get_user(message.from_user.id, message.from_user.username)

    await state.clear()

    welcome_text = (
        f"🎯 <b>Добро пожаловать в QuizBot!</b>\n\n"
        f"Привет, {message.from_user.first_name}!\n"
        f"Твоя статистика:\n"
        f"🏆 Всего очков: {user.total_score}\n"
        f"📊 Игр сыграно: {user.games_played}\n"
        f"✅ Правильных ответов: {user.correct_answers}\n"
        f"📝 Всего ответов: {user.total_answers}\n"
        f"📈 Точность: {user.correct_answers / max(user.total_answers, 1) * 100:.1f}%\n\n"
        f"Выбери категорию вопросов:"
    )

    await message.answer(
        welcome_text,
        reply_markup=get_categories_keyboard(),
        parse_mode="HTML"
    )

    # Команда помощи
    @dp.message(Command("help"))
    async def cmd_help(message: types.Message):
        help_text = (
            "📚 <b>Помощь по боту</b>\n\n"
            "Команды:\n"
            "/start - Начать игру и показать статистику\n"
            "/help - Показать это сообщение\n"
            "/stats - Показать твою статистику\n"
            "/menu - Вернуться в главное меню\n\n"
            "Как играть:\n"
            "1. Выбери категорию вопросов\n"
            "2. Отвечай на вопросы, нажимая на кнопки\n"
            "3. За каждый правильный ответ получаешь 10 очков\n"
            "4. В конце игры увидишь свой результат\n\n"
            "Удачи! 🍀"
        )
        await message.answer(help_text, parse_mode="HTML")

    # Команда статистики
    @dp.message(Command("stats"))
    async def cmd_stats(message: types.Message):
        user = get_user(message.from_user.id, message.from_user.username)

        stats_text = (
            f"📊 <b>Твоя статистика</b>\n\n"
            f"👤 Пользователь: {message.from_user.full_name}\n"
            f"🏆 Всего очков: {user.total_score}\n"
            f"📊 Игр сыграно: {user.games_played}\n"
            f"✅ Правильных ответов: {user.correct_answers}\n"
            f"❌ Неправильных ответов: {user.total_answers - user.correct_answers}\n"
            f"📝 Всего ответов: {user.total_answers}\n"
            f"📈 Точность: {user.correct_answers / max(user.total_answers, 1) * 100:.1f}%"
        )

        await message.answer(stats_text, parse_mode="HTML")

    # Команда меню
    @dp.message(Command("menu"))
    async def cmd_menu(message: types.Message, state: FSMContext):
        await state.clear()
        await cmd_start(message, state)

    # Обработчик выбора категории
    @dp.callback_query(lambda c: c.data.startswith("cat_"))
    async def process_category(callback: CallbackQuery, state: FSMContext):
        category = callback.data.replace("cat_", "")

        if category == "random":
            category = random.choice(list(QUESTIONS.keys()))

        # Получаем вопросы для категории и перемешиваем их
        questions = QUESTIONS.get(category, [])
        if not questions:
            await callback.message.edit_text(
                "❌ В этой категории пока нет вопросов. Выбери другую.",
                reply_markup=get_categories_keyboard()
            )
            await callback.answer()
            return

        # Копируем и перемешиваем вопросы
        shuffled_questions = random.sample(questions, len(questions))

        # Создаем новую игру
        game = GameState(category, shuffled_questions)

        # Сохраняем состояние игры
        await state.update_data(game=game)
        await state.set_state(QuizStates.playing)

        # Отправляем первый вопрос
        await send_question(callback.message, game, state)
        await callback.answer()

    # Отправка вопроса
    async def send_question(message: types.Message, game: GameState, state: FSMContext):
        question = game.get_current_question()
        if not question:
            return

        progress = f"Вопрос {game.current_index + 1} из {len(game.questions)}"
        score_text = f"💰 Счёт: {game.score}"

        question_text = (
            f"<b>Категория: {get_category_name(game.category)}</b>\n"
            f"{progress} | {score_text}\n\n"
            f"❓ {question['question']}"
        )

        await message.answer(
            question_text,
            reply_markup=get_answers_keyboard(question['options'], game.current_index),
            parse_mode="HTML"
        )

    # Получение названия категории
    def get_category_name(category: str) -> str:
        categories = {
            "history": "История",
            "science": "Наука",
            "geography": "География"
        }
        return categories.get(category, category)

    # Обработчик ответов
    @dp.callback_query(lambda c: c.data.startswith("answer_"), QuizStates.playing)
    async def process_answer(callback: CallbackQuery, state: FSMContext):
        # Парсим callback_data
        _, question_index, answer_index = callback.data.split("_")
        question_index = int(question_index)
        answer_index = int(answer_index)

        # Получаем состояние игры
        data = await state.get_data()
        game: GameState = data.get('game')

        if not game or game.is_finished() or game.current_index != question_index:
            await callback.answer("Этот вопрос уже неактуален!")
            return

        # Получаем текущий вопрос
        question = game.get_current_question()

        # Проверяем правильность ответа

    is_correct = (answer_index == question['correct'])

    # Обновляем статистику
    user = get_user(callback.from_user.id, callback.from_user.username)
    user.total_answers += 1

    if is_correct:
        game.score += 10
        user.correct_answers += 1
        user.total_score += 10
        result_text = "✅ <b>Правильно!</b>"
    else:
        correct_option = question['options'][question['correct']]
        result_text = f"❌ <b>Неправильно!</b>\nПравильный ответ: {correct_option}"

    # Добавляем объяснение
    result_text += f"\n\n💡 {question['explanation']}"

    # Сохраняем ответ
    game.answers.append({
        'question': question['question'],
        'user_answer': question['options'][answer_index],
        'correct': is_correct
    })

    # Переходим к следующему вопросу
    game.current_index += 1

    # Сохраняем обновленную игру
    await state.update_data(game=game)

    # Отправляем результат
    await callback.message.edit_text(
        result_text,
        parse_mode="HTML",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[[
            InlineKeyboardButton(text="➡️ Далее", callback_data="next_question")
        ]])
    )

    await callback.answer()

    # Сохраняем данные пользователя
    save_user_data()


# Обработчик перехода к следующему вопросу
@dp.callback_query(lambda c: c.data == "next_question", QuizStates.playing)
async def process_next(callback: CallbackQuery, state: FSMContext):
    data = await state.get_data()
    game: GameState = data.get('game')

    if not game:
        await state.clear()
        await callback.message.edit_text(
            "Игра завершена. Начни новую игру с /start",
            reply_markup=get_categories_keyboard()
        )
        await callback.answer()
        return

    if game.is_finished():
        # Игра завершена
        await finish_game(callback.message, game, state)
        await callback.answer()
        return
