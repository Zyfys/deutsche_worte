from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from database import ensure_user, get_active_session
from services.gemini import lookup_word
from services.word_service import format_lookup_message

_MENU_BTN = InlineKeyboardMarkup([[InlineKeyboardButton("🏠 Главное меню", callback_data="menu:main")]])


async def handle_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    ensure_user(user.id, user.username)

    word = update.message.text.strip()

    if word.startswith("/"):
        return

    # Если идёт разговорная практика — передаём туда
    session = get_active_session(user.id)
    if session and session["session_type"] == "conversation":
        from handlers.practice import practice_message
        await practice_message(update, context)
        return

    # Если идёт письменная практика — передаём туда
    if session and session["session_type"] == "writing":
        from handlers.writing import writing_submit
        await writing_submit(update, context)
        return

    # Если идёт экзамен Goethe — передаём туда
    if session and session["session_type"] == "goethe_exam":
        from handlers.goethe_exam import goethe_answer
        await goethe_answer(update, context)
        return

    # Если идёт открытое задание по грамматике — передаём туда
    from handlers.grammar import grammar_handle_open, _grammar_state
    if user.id in _grammar_state and _grammar_state[user.id].get("phase") == "open":
        await grammar_handle_open(update, context)
        return

    # Обычный поиск слова
    if len(word.split()) > 3:
        await update.message.reply_text(
            "📝 Отправь одно немецкое слово или короткое словосочетание,\n"
            "и я дам перевод, формы и примеры.\n\n"
            "Или начни практику: /practice"
        )
        return

    await update.message.reply_text(f"🔍 Ищу «{word}»...")

    try:
        data = lookup_word(word)
    except Exception as e:
        await update.message.reply_text(f"❌ Не удалось найти слово: {e}")
        return

    msg = format_lookup_message(data)
    await update.message.reply_text(msg, parse_mode="Markdown", reply_markup=_MENU_BTN)
