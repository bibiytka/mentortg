import os
from dotenv import load_dotenv

# Загружаем переменные окружения
load_dotenv()

# Telegram Bot Settings
BOT_TOKEN = os.getenv("BOT_TOKEN")
if not BOT_TOKEN:
    raise ValueError("BOT_TOKEN не найден в переменных окружения!")

# OpenAI Settings
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
if not OPENAI_API_KEY:
    raise ValueError("OPENAI_API_KEY не найден в переменных окружения!")

# Администраторы (ID пользователей Telegram)
SUPER_ADMINS = [
    int(admin_id) for admin_id in os.getenv("SUPER_ADMINS", "").split(",") if admin_id.strip()
]
ADMINS = [
    int(admin_id) for admin_id in os.getenv("ADMINS", "").split(",") if admin_id.strip()
]

# Все админы (супер-админы + обычные админы)
ALL_ADMINS = list(set(SUPER_ADMINS + ADMINS))

# Настройки базы данных
DATABASE_PATH = "bot.db"

# Настройки OpenAI
OPENAI_MODEL = "gpt-4o-mini"  # Более новая и дешевая модель
OPENAI_TEMPERATURE = 0.3
OPENAI_MAX_TOKENS = 1000

# Настройки пагинации
USERS_PER_PAGE = 10

# Папки проекта
PROMPTS_DIR = "prompts/templates"

# Лимиты
MAX_THEORY_TEXT_LENGTH = 100000
MAX_QUESTION_TEXT_LENGTH = 5000
MAX_ANSWER_LENGTH = 10000