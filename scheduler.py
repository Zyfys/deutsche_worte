import logging
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from telegram import InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application
from database import get_all_user_ids, get_sent_words, save_word
from services.groq_service import generate_daily_word
from services.word_service import format_word_message

_MENU_BTN = InlineKeyboardMarkup([[InlineKeyboardButton("🏠 Главное меню", callback_data="menu:main")]])
from config import (
    DAILY_WORD_HOUR, DAILY_WORD_MINUTE,
    WEEKLY_QUIZ_HOUR, WEEKLY_QUIZ_MINUTE, WEEKLY_QUIZ_DAY,
    MONTHLY_EXAM_HOUR, MONTHLY_EXAM_MINUTE, MONTHLY_EXAM_DAY,
    QUIZ_WORD_COUNT, EXAM_WORD_COUNT,
)

logger = logging.getLogger(__name__)


async def send_daily_words(app: Application):
    user_ids = get_all_user_ids()
    logger.info(f"Sending daily word to {len(user_ids)} users")

    for user_id in user_ids:
        try:
            used = get_sent_words(user_id)
            data = generate_daily_word(used)
            save_word(user_id, data["word"], data)
            msg = format_word_message(data)
            await app.bot.send_message(user_id, msg, parse_mode="Markdown", reply_markup=_MENU_BTN)
        except Exception as e:
            logger.error(f"Failed to send daily word to {user_id}: {e}")


async def send_weekly_quiz(app: Application):
    from database import get_words_for_quiz, create_quiz
    import random
    from config import QUIZ_OPTIONS_COUNT
    from handlers.quiz import _quiz_state

    user_ids = get_all_user_ids()
    logger.info(f"Starting weekly quiz for {len(user_ids)} users")

    for user_id in user_ids:
        try:
            words = get_words_for_quiz(user_id, QUIZ_WORD_COUNT, days=7)
            if len(words) < 4:
                await app.bot.send_message(
                    user_id,
                    "📅 *Время еженедельной викторины!*\n\n"
                    f"У тебя пока недостаточно слов за неделю ({len(words)} из 4 минимум).\n"
                    "Продолжай учить слова! 💪",
                    parse_mode="Markdown"
                )
                continue

            quiz_id = create_quiz(user_id, "weekly", len(words))
            _quiz_state[user_id] = {
                "quiz_id": quiz_id,
                "words": words,
                "index": 0,
                "score": 0,
                "quiz_type": "weekly",
            }

            await app.bot.send_message(
                user_id,
                "🏁 *Еженедельная викторина начинается!*\n"
                f"Слов: {len(words)}\n\n"
                "Отвечай на вопросы, нажимая кнопки 👇",
                parse_mode="Markdown"
            )

            from handlers.quiz import _build_question
            text, keyboard, _ = _build_question(words, 0)
            await app.bot.send_message(user_id, text, reply_markup=keyboard, parse_mode="Markdown")

        except Exception as e:
            logger.error(f"Failed to start weekly quiz for {user_id}: {e}")


async def send_monthly_exam(app: Application):
    from database import get_words_for_quiz, create_quiz
    from handlers.quiz import _quiz_state, _build_question

    user_ids = get_all_user_ids()
    logger.info(f"Starting monthly exam for {len(user_ids)} users")

    for user_id in user_ids:
        try:
            words = get_words_for_quiz(user_id, EXAM_WORD_COUNT, days=31)
            if len(words) < 4:
                await app.bot.send_message(
                    user_id,
                    "📋 *Время ежемесячного экзамена!*\n\n"
                    f"У тебя пока недостаточно слов за месяц ({len(words)} из 4 минимум).\n"
                    "Продолжай учить слова! 💪",
                    parse_mode="Markdown"
                )
                continue

            quiz_id = create_quiz(user_id, "monthly", len(words))
            _quiz_state[user_id] = {
                "quiz_id": quiz_id,
                "words": words,
                "index": 0,
                "score": 0,
                "quiz_type": "monthly",
            }

            await app.bot.send_message(
                user_id,
                "📋 *Ежемесячный экзамен начинается!*\n"
                f"Слов: {len(words)}\n\n"
                "Отвечай на вопросы, нажимая кнопки 👇",
                parse_mode="Markdown"
            )

            text, keyboard, _ = _build_question(words, 0)
            await app.bot.send_message(user_id, text, reply_markup=keyboard, parse_mode="Markdown")

        except Exception as e:
            logger.error(f"Failed to start monthly exam for {user_id}: {e}")


def setup_scheduler(app: Application) -> AsyncIOScheduler:
    scheduler = AsyncIOScheduler(timezone="UTC")

    scheduler.add_job(
        send_daily_words,
        CronTrigger(hour=DAILY_WORD_HOUR, minute=DAILY_WORD_MINUTE),
        args=[app],
        id="daily_word",
        name="Daily word",
    )

    scheduler.add_job(
        send_weekly_quiz,
        CronTrigger(day_of_week=WEEKLY_QUIZ_DAY, hour=WEEKLY_QUIZ_HOUR, minute=WEEKLY_QUIZ_MINUTE),
        args=[app],
        id="weekly_quiz",
        name="Weekly quiz",
    )

    scheduler.add_job(
        send_monthly_exam,
        CronTrigger(day=MONTHLY_EXAM_DAY, hour=MONTHLY_EXAM_HOUR, minute=MONTHLY_EXAM_MINUTE),
        args=[app],
        id="monthly_exam",
        name="Monthly exam",
    )

    return scheduler
