import asyncio
import logging
import sys
import urllib.request
from config import WEBHOOK_HOST
from threading import Thread

from aiogram import Bot, Dispatcher
from aiogram.enums import ParseMode
from aiogram.client.default import DefaultBotProperties
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.types import Update
from flask import Flask, request

from config import (
    BOT_TOKEN, WEBHOOK_URL, WEBHOOK_PATH,
    WEBAPP_HOST, WEBAPP_PORT
)
from database import init_db
from handlers import start, menu, quiz, xml_handler

# ───────────── ЛОГИРОВАНИЕ ─────────────

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
    datefmt="%H:%M:%S"
)
logger = logging.getLogger(__name__)

# ───────────── FLASK + AIOGRAM ─────────────

flask_app = Flask(__name__)
bot = Bot(
    token=BOT_TOKEN,
    default=DefaultBotProperties(parse_mode=ParseMode.HTML)
)
dp = Dispatcher(storage=MemoryStorage())

dp.include_router(start.router)
dp.include_router(menu.router)
dp.include_router(quiz.router)
dp.include_router(xml_handler.router)

loop = asyncio.new_event_loop()


# ───────────── WEBHOOK ENDPOINT ─────────────

@flask_app.route(WEBHOOK_PATH, methods=["POST"])
def webhook():
    """Принимает обновления от Telegram"""
    data = request.get_json()
    if not data:
        return "Bad Request", 400

    update = Update(**data)
    asyncio.run_coroutine_threadsafe(
        dp.feed_update(bot, update),
        loop
    )
    return "OK", 200


@flask_app.route("/", methods=["GET"])
def index():
    """Health check для Render"""
    return "✅ Quiz Bot is running!", 200


# ───────────── ЗАПУСК ─────────────
async def keep_alive():
    """Пингует сервер каждые 10 минут чтобы не засыпал"""
    while True:
        await asyncio.sleep(600)  # 10 минут
        try:
            urllib.request.urlopen(WEBHOOK_HOST)
            logger.info("♻️ Keep-alive ping отправлен")
        except Exception:
            pass


async def on_startup():
    await init_db()
    await bot.set_webhook(WEBHOOK_URL)
    logger.info(f"✅ Webhook установлен: {WEBHOOK_URL}")
    asyncio.run_coroutine_threadsafe(keep_alive(), loop)


def start_event_loop():
    """Запускает asyncio loop в отдельном потоке"""
    asyncio.set_event_loop(loop)
    loop.run_until_complete(on_startup())
    loop.run_forever()


if __name__ == "__main__":
    if sys.platform == "win32":
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

    # Запускаем asyncio loop в фоновом потоке
    thread = Thread(target=start_event_loop, daemon=True)
    thread.start()

    logger.info(f"🚀 Flask сервер запущен на порту {WEBAPP_PORT}")

    # Запускаем Flask
    flask_app.run(
        host=WEBAPP_HOST,
        port=WEBAPP_PORT
    )