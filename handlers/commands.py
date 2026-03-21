from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes, CallbackQueryHandler
from database import ensure_user, get_word_count, get_quiz_history
from services.gemini import generate_daily_word
from services.word_service import format_word_message
from database import get_sent_words, save_word


def _main_menu_keyboard():
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton("📖 Слово сейчас",  callback_data="menu:word_now"),
            InlineKeyboardButton("📊 Статистика",    callback_data="menu:stats"),
        ],
        [
            InlineKeyboardButton("🎭 Практика",      callback_data="menu:practice"),
            InlineKeyboardButton("✍️ Письмо",        callback_data="menu:write"),
        ],
        [
            InlineKeyboardButton("🎓 Goethe экзамен", callback_data="menu:goethe"),
            InlineKeyboardButton("📐 Грамматика",     callback_data="menu:grammar"),
        ],
        [
            InlineKeyboardButton("❓ Помощь",        callback_data="menu:help"),
        ],
    ])


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    ensure_user(user.id, user.username)
    await update.message.reply_text(
        "👋 Привет! Я помогу подготовиться к *Goethe-Zertifikat*.\n\n"
        "📅 Каждый день в 11:00 МСК — новое немецкое слово\n"
        "📝 Напиши слово — получи перевод и примеры\n"
        "🎙️ Отправь голосовое — распознаю и переведу\n\n"
        "Выбери раздел:",
        reply_markup=_main_menu_keyboard(),
        parse_mode="Markdown"
    )


async def menu_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    action = query.data.split(":")[1]

    # Для команд без диалога — просто вызываем функцию
    if action == "word_now":
        await query.message.reply_text("⏳ Генерирую слово...")
        user = query.from_user
        ensure_user(user.id, user.username)
        used = get_sent_words(user.id)
        try:
            data = generate_daily_word(used)
        except Exception as e:
            await query.message.reply_text(f"❌ Ошибка: {e}")
            return
        save_word(user.id, data["word"], data)
        menu_btn = InlineKeyboardMarkup([[InlineKeyboardButton("🏠 Главное меню", callback_data="menu:main")]])
        await query.message.reply_text(format_word_message(data), parse_mode="Markdown", reply_markup=menu_btn)

    elif action == "stats":
        user = query.from_user
        ensure_user(user.id, user.username)
        count = get_word_count(user.id)
        history = get_quiz_history(user.id, limit=5)
        text = f"📊 *Твоя статистика*\n\n📚 Выучено слов: *{count}*\n"
        if history:
            text += "\n🏆 *Последние результаты:*\n"
            for q in history:
                emoji = "📝" if q["quiz_type"] == "weekly" else "📋"
                label = "Викторина" if q["quiz_type"] == "weekly" else "Экзамен"
                date = q["started_at"].strftime("%d.%m.%Y")
                pct = round(q["score"] / q["total"] * 100) if q["total"] else 0
                text += f"{emoji} {label} {date}: {q['score']}/{q['total']} ({pct}%)\n"
        else:
            text += "\nПока нет завершённых викторин."
        await query.message.reply_text(text, parse_mode="Markdown")

    elif action == "main":
        await query.message.reply_text(
            "👋 Главное меню:",
            reply_markup=_main_menu_keyboard()
        )

    elif action == "help":
        await _send_help(query.message)

    elif action == "practice":
        buttons = InlineKeyboardMarkup([
            [InlineKeyboardButton("A2", callback_data="practice_level:A2"),
             InlineKeyboardButton("B1", callback_data="practice_level:B1")],
            [InlineKeyboardButton("B2", callback_data="practice_level:B2"),
             InlineKeyboardButton("C1", callback_data="practice_level:C1")],
        ])
        await query.message.reply_text(
            "🎭 *Разговорная практика*\n\nВыбери уровень сложности:",
            reply_markup=buttons,
            parse_mode="Markdown"
        )

    elif action == "write":
        buttons = InlineKeyboardMarkup([
            [InlineKeyboardButton("A2", callback_data="write_level:A2"),
             InlineKeyboardButton("B1", callback_data="write_level:B1")],
            [InlineKeyboardButton("B2", callback_data="write_level:B2"),
             InlineKeyboardButton("C1", callback_data="write_level:C1")],
        ])
        await query.message.reply_text(
            "✍️ *Письменная практика*\n\nВыбери уровень:",
            reply_markup=buttons,
            parse_mode="Markdown"
        )

    elif action == "goethe":
        buttons = InlineKeyboardMarkup([
            [InlineKeyboardButton("A2", callback_data="goethe_level:A2"),
             InlineKeyboardButton("B1", callback_data="goethe_level:B1")],
            [InlineKeyboardButton("B2", callback_data="goethe_level:B2"),
             InlineKeyboardButton("C1", callback_data="goethe_level:C1")],
        ])
        await query.message.reply_text(
            "📋 *Симулятор Goethe-Zertifikat*\n\nВыбери уровень:",
            reply_markup=buttons,
            parse_mode="Markdown"
        )

    elif action == "grammar":
        buttons = InlineKeyboardMarkup([
            [InlineKeyboardButton("A1", callback_data="grammar_level:A1"),
             InlineKeyboardButton("A2", callback_data="grammar_level:A2"),
             InlineKeyboardButton("B1", callback_data="grammar_level:B1")],
        ])
        await query.message.reply_text(
            "📐 *Грамматика*\n\nВыбери уровень:",
            reply_markup=buttons,
            parse_mode="Markdown"
        )

    else:
        await query.message.reply_text(f"/{action}", parse_mode="Markdown")


async def _send_help(message):
    await message.reply_text(
        "❓ *Все команды*\n\n"

        "━━━ 📖 *Слова* ━━━\n"
        "/word\\_now — слово дня прямо сейчас\n"
        "  _Gemini генерирует слово уровня A2–B1 из списка Goethe с переводом, примерами и формами_\n\n"
        "/quiz\\_now — викторина по твоим словам\n"
        "  _4 варианта ответа, нужно минимум 4 выученных слова_\n\n"
        "/exam\\_now — месячный экзамен\n"
        "  _Все слова за последний месяц, нужно минимум 4 слова_\n\n"

        "━━━ 📐 *Грамматика* ━━━\n"
        "/grammar — темы грамматики по уровням\n"
        "  _Объяснение правил + тесты с вариантами + открытые задания_\n\n"

        "━━━ 🎭 *Практика* ━━━\n"
        "/practice — разговорный диалог с AI\n"
        "  _Выбери уровень (A2–C1) и сценарий: кафе, аэропорт, врач и др. Бот исправляет ошибки в реальном времени_\n\n"
        "/write — письменное задание\n"
        "  _Задание в стиле Goethe, оценка по 4 критериям: Aufgabe, Kohärenz, Ausdruck, Korrektheit_\n\n"
        "/goethe — симулятор экзамена Goethe\n"
        "  _Полный формат: Hören, Lesen, Schreiben, Sprechen_\n\n"
        "/stop — завершить практику\n"
        "  _Останавливает диалог и показывает итоговую оценку с разбором ошибок_\n\n"

        "━━━ 📊 *Прогресс* ━━━\n"
        "/stats — твоя статистика\n"
        "  _Количество слов, результаты викторин и экзаменов_\n\n"

        "━━━ 💡 *Советы* ━━━\n"
        "• Напиши любое немецкое слово — получи перевод и примеры\n"
        "• Отправь 🎤 голосовое — распознаю и переведу\n"
        "• Слово дня приходит автоматически в 11:00 МСК",
        parse_mode="Markdown"
    )


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await _send_help(update.message)


async def stats(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    ensure_user(user.id, user.username)

    count = get_word_count(user.id)
    history = get_quiz_history(user.id, limit=5)

    text = f"📊 *Твоя статистика*\n\n📚 Выучено слов: *{count}*\n"

    if history:
        text += "\n🏆 *Последние результаты:*\n"
        for q in history:
            emoji = "📝" if q["quiz_type"] == "weekly" else "📋"
            label = "Викторина" if q["quiz_type"] == "weekly" else "Экзамен"
            date = q["started_at"].strftime("%d.%m.%Y")
            pct = round(q["score"] / q["total"] * 100) if q["total"] else 0
            text += f"{emoji} {label} {date}: {q['score']}/{q['total']} ({pct}%)\n"
    else:
        text += "\nПока нет завершённых викторин."

    await update.message.reply_text(text, parse_mode="Markdown")


async def word_now(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    ensure_user(user.id, user.username)

    await update.message.reply_text("⏳ Генерирую слово...")

    used = get_sent_words(user.id)
    try:
        data = generate_daily_word(used)
    except Exception as e:
        await update.message.reply_text(f"❌ Ошибка при генерации слова: {e}")
        return

    save_word(user.id, data["word"], data)
    menu_btn = InlineKeyboardMarkup([[InlineKeyboardButton("🏠 Главное меню", callback_data="menu:main")]])
    await update.message.reply_text(format_word_message(data), parse_mode="Markdown", reply_markup=menu_btn)
