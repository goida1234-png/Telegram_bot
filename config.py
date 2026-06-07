from dotenv import load_dotenv
import os

load_dotenv()

BOT_TOKEN    = os.getenv("BOT_TOKEN")
WEBHOOK_HOST = os.getenv("WEBHOOK_HOST", "")   # https://your-app.onrender.com
WEBHOOK_PATH = f"/webhook/{BOT_TOKEN}"
WEBHOOK_URL  = f"{WEBHOOK_HOST}{WEBHOOK_PATH}"

# Flask сервер
WEBAPP_HOST = "0.0.0.0"
WEBAPP_PORT = int(os.getenv("PORT", 8080))      # Render сам задаёт PORT

DB_NAME = "quiz.db"