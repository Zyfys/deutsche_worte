import os
from dotenv import load_dotenv

load_dotenv()

TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
GROQ_API_KEY = os.getenv("GROQ_API_KEY")
GROQ_MODEL = os.getenv("GROQ_MODEL", "llama-3.3-70b-versatile")
DATABASE_URL = os.getenv("DATABASE_URL")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")  # Для Whisper, необязателен если не используешь голос

if not TELEGRAM_BOT_TOKEN:
    raise ValueError("TELEGRAM_BOT_TOKEN is not set in .env")
if not GROQ_API_KEY:
    raise ValueError("GROQ_API_KEY is not set in .env")
if not DATABASE_URL:
    raise ValueError("DATABASE_URL is not set in .env")

# Время отправки (UTC). Для Москвы (UTC+3) вычтите 3 часа.
DAILY_WORD_HOUR = 8    # 11:00 МСК
DAILY_WORD_MINUTE = 0

WEEKLY_QUIZ_HOUR = 7   # 10:00 МСК
WEEKLY_QUIZ_MINUTE = 0
WEEKLY_QUIZ_DAY = "sun"  # воскресенье

MONTHLY_EXAM_HOUR = 7  # 10:00 МСК
MONTHLY_EXAM_MINUTE = 0
MONTHLY_EXAM_DAY = 1   # 1-е число

QUIZ_WORD_COUNT = 7
EXAM_WORD_COUNT = 20
QUIZ_OPTIONS_COUNT = 4  # количество вариантов ответа
