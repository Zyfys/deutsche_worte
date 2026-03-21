import random
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes, CallbackQueryHandler, CommandHandler
from database import (
    ensure_user, get_words_for_quiz,
    create_quiz, save_quiz_answer, finish_quiz, get_wrong_answers
)
from config import QUIZ_WORD_COUNT, EXAM_WORD_COUNT, QUIZ_OPTIONS_COUNT

# Хранилище состояния викторины в памяти: {user_id: quiz_state}
_quiz_state: dict[int, dict] = {}


def _build_question(words: list[dict], index: int) -> tuple[str, InlineKeyboardMarkup, str]:
    """Строит вопрос: показывает немецкое слово, предлагает 4 варианта перевода."""
    current = words[index]
    word_data = current["word_data"]
    correct = word_data["translation"]

    # Собираем все доступные переводы кроме правильного для вариантов
    all_translations = [
        w["word_data"]["translation"]
        for w in words
        if w["word_data"]["translation"] != correct
    ]
    wrong_options = random.sample(all_translations, min(QUIZ_OPTIONS_COUNT - 1, len(all_translations)))

    options = wrong_options + [correct]
    random.shuffle(options)

    article = word_data.get("article", "")
    display_word = f"{article} {current['word']}".strip() if article else current["word"]

    text = (
        f"❓ *Вопрос {index + 1}/{len(words)}*\n\n"
        f"🎯 *{display_word}*\n\n"
        "Выбери правильный перевод:"
    )

    buttons = [
        [InlineKeyboardButton(opt, callback_data=f"quiz:{opt}")]
        for opt in options
    ]
    return text, InlineKeyboardMarkup(buttons), correct


async def _start_quiz_flow(update: Update, context: ContextTypes.DEFAULT_TYPE, quiz_type: str):
    user = update.effective_user
    ensure_user(user.id, user.username)

    count = QUIZ_WORD_COUNT if quiz_type == "weekly" else EXAM_WORD_COUNT
    days = 7 if quiz_type == "weekly" else 31

    words = get_words_for_quiz(user.id, count, days)

    if len(words) < 4:
        label = "викторины" if quiz_type == "weekly" else "экзамена"
        await update.message.reply_text(
            f"📚 Для {label} нужно минимум 4 слова.\n"
            f"У тебя пока {len(words)} слов за нужный период.\n"
            "Продолжай учить слова каждый день! 💪"
        )
        return

    quiz_id = create_quiz(user.id, quiz_type, len(words))
    _quiz_state[user.id] = {
        "quiz_id": quiz_id,
        "words": words,
        "index": 0,
        "score": 0,
        "quiz_type": quiz_type,
    }

    label = "Викторина" if quiz_type == "weekly" else "Экзамен"
    await update.message.reply_text(
        f"🏁 *{label} начинается!*\n"
        f"Слов: {len(words)}\n\n"
        "Отвечай на вопросы, нажимая кнопки 👇",
        parse_mode="Markdown"
    )

    text, keyboard, _ = _build_question(words, 0)
    await update.message.reply_text(text, reply_markup=keyboard, parse_mode="Markdown")


async def quiz_now(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await _start_quiz_flow(update, context, "weekly")


async def exam_now(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await _start_quiz_flow(update, context, "monthly")


async def handle_quiz_answer(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    user_id = query.from_user.id
    state = _quiz_state.get(user_id)

    if not state:
        await query.edit_message_text("❌ Викторина не найдена. Запусти заново командой /quiz_now")
        return

    chosen = query.data.replace("quiz:", "", 1)
    words = state["words"]
    index = state["index"]
    current = words[index]
    correct = current["word_data"]["translation"]
    is_correct = chosen == correct

    save_quiz_answer(state["quiz_id"], current["word"], correct, chosen, is_correct)

    if is_correct:
        state["score"] += 1
        feedback = f"✅ *Правильно!* {correct}"
    else:
        feedback = f"❌ *Неверно.*\nПравильный ответ: *{correct}*"

    await query.edit_message_text(feedback, parse_mode="Markdown")

    state["index"] += 1

    if state["index"] >= len(words):
        # Викторина завершена
        score = state["score"]
        total = len(words)
        finish_quiz(state["quiz_id"], score)
        wrong = get_wrong_answers(state["quiz_id"])
        del _quiz_state[user_id]

        pct = round(score / total * 100)
        label = "Викторина" if state["quiz_type"] == "weekly" else "Экзамен"

        if pct >= 80:
            grade_emoji = "🌟"
        elif pct >= 60:
            grade_emoji = "👍"
        else:
            grade_emoji = "📖"

        result_text = (
            f"{grade_emoji} *{label} завершён!*\n\n"
            f"Результат: *{score}/{total}* ({pct}%)\n"
        )

        if wrong:
            result_text += "\n❌ *Ошибки:*\n"
            for w in wrong:
                result_text += f"• {w['word']} → {w['correct_answer']}\n"

        if pct < 80:
            result_text += "\n💡 Повтори слова с ошибками!"

        await context.bot.send_message(user_id, result_text, parse_mode="Markdown")
    else:
        # Следующий вопрос
        text, keyboard, _ = _build_question(words, state["index"])
        await context.bot.send_message(user_id, text, reply_markup=keyboard, parse_mode="Markdown")


def get_quiz_handlers():
    return [
        CommandHandler("quiz_now", quiz_now),
        CommandHandler("exam_now", exam_now),
        CallbackQueryHandler(handle_quiz_answer, pattern=r"^quiz:"),
    ]
