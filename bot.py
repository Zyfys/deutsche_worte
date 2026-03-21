import logging
from telegram import Update, BotCommand
from telegram.ext import Application, CommandHandler, MessageHandler, CallbackQueryHandler, filters
from config import TELEGRAM_BOT_TOKEN
from database import init_db
from handlers.commands import start, help_command, stats, word_now, menu_callback
from handlers.messages import handle_text
from handlers.voice import handle_voice
from handlers.quiz import get_quiz_handlers
from handlers.practice import get_practice_handlers
from handlers.writing import get_writing_handlers
from handlers.goethe_exam import get_goethe_handlers
from handlers.grammar import get_grammar_handlers
from scheduler import setup_scheduler

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger(__name__)


async def post_init(application: Application):
    scheduler = setup_scheduler(application)
    application.bot_data["scheduler"] = scheduler
    scheduler.start()
    logger.info("Scheduler started")

    await application.bot.set_my_commands([
        BotCommand("start",      "🏠 Главное меню"),
        BotCommand("word_now",   "📖 Получить слово прямо сейчас"),
        BotCommand("practice",   "🎭 Разговорная практика (A2–C1)"),
        BotCommand("write",      "✍️ Письменная практика с оценкой"),
        BotCommand("goethe",     "🎓 Симулятор экзамена Goethe"),
        BotCommand("stop",       "🛑 Завершить практику и получить оценку"),
        BotCommand("quiz_now",   "🧠 Запустить викторину по словам"),
        BotCommand("exam_now",   "📋 Запустить месячный экзамен"),
        BotCommand("grammar",    "📐 Грамматика по темам (A1–B1)"),
        BotCommand("stats",      "📊 Моя статистика"),
        BotCommand("help",       "❓ Все команды и описание"),
    ])


async def post_shutdown(application: Application):
    if "scheduler" in application.bot_data:
        application.bot_data["scheduler"].shutdown()


def main():
    init_db()
    logger.info("Database initialized")

    app = (
        Application.builder()
        .token(TELEGRAM_BOT_TOKEN)
        .post_init(post_init)
        .post_shutdown(post_shutdown)
        .build()
    )

    # Основные команды
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("help", help_command))
    app.add_handler(CommandHandler("stats", stats))
    app.add_handler(CommandHandler("word_now", word_now))

    # Кнопки главного меню
    app.add_handler(CallbackQueryHandler(menu_callback, pattern=r"^menu:"))

    # Викторина и экзамен (старые)
    for handler in get_quiz_handlers():
        app.add_handler(handler)

    # Разговорная практика
    for handler in get_practice_handlers():
        app.add_handler(handler)

    # Письменная практика
    for handler in get_writing_handlers():
        app.add_handler(handler)

    # Симулятор Goethe
    for handler in get_goethe_handlers():
        app.add_handler(handler)

    # Грамматика
    for handler in get_grammar_handlers():
        app.add_handler(handler)

    # Голосовые сообщения
    app.add_handler(MessageHandler(filters.VOICE, handle_voice))

    # Текстовые сообщения (поиск слова + роутинг в практику)
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text))

    logger.info("Bot is running...")
    app.run_polling(drop_pending_updates=True, allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()
