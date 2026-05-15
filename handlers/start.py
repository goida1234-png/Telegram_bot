from aiogram import Router
from aiogram.filters import CommandStart
from aiogram.types import Message

from database import get_or_create_user
from keyboards import main_menu_kb

router = Router()


def get_welcome_text(first_name: str) -> str:
    return (
        f"👋 Привет, <b>{first_name}</b>!\n\n"
        f"🎯 Добро пожаловать в <b>Викторину</b>!\n\n"
        f"📚 Здесь тебя ждут вопросы по темам:\n"
        f"   🎮 Dota 2\n"
        f"   🔫 CS2 / CS:GO\n"
        f"   ⚽ Футбол\n"
        f"   🧠 Общие знания\n\n"
        f"🏆 Каждая глава — <b>20 вопросов</b>.\n"
        f"💾 Твои результаты сохраняются автоматически.\n\n"
        f"Выбери действие 👇"
    )


@router.message(CommandStart())
async def cmd_start(message: Message):
    await get_or_create_user(
        tg_id=message.from_user.id,
        username=message.from_user.username or "",
        first_name=message.from_user.first_name or "Игрок"
    )

    # Удаляем сообщение пользователя /start чтобы не засорять чат
    try:
        await message.delete()
    except Exception:
        pass

    await message.answer(
        text=get_welcome_text(message.from_user.first_name or "Игрок"),
        reply_markup=main_menu_kb(),
        parse_mode="HTML"
    )