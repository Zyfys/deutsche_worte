import json
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes, CommandHandler, CallbackQueryHandler

with open("data/grammar.json", encoding="utf-8") as f:
    GRAMMAR = json.load(f)

LEVELS = ["A1", "A2", "B1"]

_MENU_BTN = InlineKeyboardMarkup([[InlineKeyboardButton("🏠 Главное меню", callback_data="menu:main")]])
_STOP_BTN = InlineKeyboardMarkup([
    [InlineKeyboardButton("⏭ Пропустить", callback_data="grammar_skip")],
    [InlineKeyboardButton("🛑 Завершить", callback_data="grammar_stop")],
])

# memory state: {user_id: {topic, level, phase, index, score, errors}}
_grammar_state: dict[int, dict] = {}


async def grammar_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    buttons = [
        [InlineKeyboardButton(l, callback_data=f"grammar_level:{l}") for l in LEVELS[i:i+2]]
        for i in range(0, len(LEVELS), 2)
    ]
    buttons.append([InlineKeyboardButton("🏠 Главное меню", callback_data="menu:main")])
    await update.message.reply_text(
        "📐 *Грамматика*\n\nВыбери уровень:",
        reply_markup=InlineKeyboardMarkup(buttons),
        parse_mode="Markdown"
    )


async def grammar_choose_level(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    level = query.data.split(":")[1]

    topics = GRAMMAR.get(level, [])
    if not topics:
        await query.message.reply_text("Темы для этого уровня пока не добавлены.")
        return

    btns = [InlineKeyboardButton(t["name"], callback_data=f"grammar_topic:{level}:{t['id']}") for t in topics]
    buttons = [btns[i:i+2] for i in range(0, len(btns), 2)]
    buttons.append([InlineKeyboardButton("🏠 Главное меню", callback_data="menu:main")])

    await query.message.reply_text(
        f"📐 *Грамматика {level}*\n\nВыбери тему:",
        reply_markup=InlineKeyboardMarkup(buttons),
        parse_mode="Markdown"
    )


async def grammar_show_topic(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    _, level, topic_id = query.data.split(":")

    topics = GRAMMAR.get(level, [])
    topic = next((t for t in topics if t["id"] == topic_id), None)
    if not topic:
        await query.message.reply_text("Тема не найдена.")
        return

    text = f"📐 *{topic['name']}*\n\n{topic['explanation']}"

    buttons = InlineKeyboardMarkup([
        [InlineKeyboardButton("▶️ Начать практику", callback_data=f"grammar_start:{level}:{topic_id}")],
        [InlineKeyboardButton("🏠 Главное меню", callback_data="menu:main")],
    ])
    await query.message.reply_text(text, reply_markup=buttons, parse_mode="Markdown")


async def grammar_begin_practice(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    _, level, topic_id = query.data.split(":")

    topics = GRAMMAR.get(level, [])
    topic = next((t for t in topics if t["id"] == topic_id), None)
    if not topic:
        await query.message.reply_text("Тема не найдена.")
        return

    user_id = query.from_user.id
    _grammar_state[user_id] = {
        "topic": topic,
        "level": level,
        "phase": "quiz",
        "index": 0,
        "score": 0,
        "errors": [],
    }

    await query.message.reply_text(
        f"📝 *Практика: {topic['name']}*\n\n"
        f"Сначала {len(topic['quiz'])} вопроса с вариантами, затем {len(topic['open'])} открытых задания.\n\n"
        "Поехали! 🚀",
        parse_mode="Markdown"
    )
    await _send_next_question(query.message, user_id)


async def _send_next_question(message, user_id: int):
    state = _grammar_state.get(user_id)
    if not state:
        return

    topic = state["topic"]
    phase = state["phase"]
    index = state["index"]

    if phase == "quiz":
        questions = topic["quiz"]
        if index >= len(questions):
            # переходим к открытым заданиям
            state["phase"] = "open"
            state["index"] = 0
            await message.reply_text(
                "✅ *Тесты пройдены!*\n\nТеперь открытые задания — напиши ответ текстом.",
                parse_mode="Markdown"
            )
            await _send_next_question(message, user_id)
            return

        q = questions[index]
        text = f"❓ Вопрос {index + 1}/{len(questions)}\n\n{q['question']}"
        btn_rows = [[InlineKeyboardButton(opt, callback_data=f"grammar_answer:{opt}")] for opt in q["options"]]
        btn_rows.append([InlineKeyboardButton("⏭ Пропустить", callback_data="grammar_skip"),
                         InlineKeyboardButton("🛑 Завершить", callback_data="grammar_stop")])
        await message.reply_text(text, reply_markup=InlineKeyboardMarkup(btn_rows))

    elif phase == "open":
        questions = topic["open"]
        if index >= len(questions):
            await _finish_grammar(message, user_id)
            return

        q = questions[index]
        total_q = len(topic["quiz"]) + len(topic["open"])
        done_q = len(topic["quiz"]) + index
        text = (
            f"✍️ Задание {done_q + 1}/{total_q}\n\n"
            f"{q['question']}\n\n"
            f"Напиши ответ текстом"
        )
        await message.reply_text(text, reply_markup=_STOP_BTN)


async def grammar_handle_answer(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обрабатывает ответ на тест с вариантами."""
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id

    state = _grammar_state.get(user_id)
    if not state or state["phase"] != "quiz":
        return

    chosen = query.data.replace("grammar_answer:", "", 1)
    topic = state["topic"]
    index = state["index"]
    q = topic["quiz"][index]
    correct = q["answer"]

    if chosen == correct:
        state["score"] += 1
        await query.message.reply_text(f"✅ Верно! *{correct}*", parse_mode="Markdown")
    else:
        state["errors"].append({"question": q["question"], "user_answer": chosen, "correct": correct})
        await query.message.reply_text(
            f"❌ Неверно. Правильный ответ: *{correct}*",
            parse_mode="Markdown"
        )

    state["index"] += 1
    await _send_next_question(query.message, user_id)


async def grammar_handle_open(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обрабатывает открытый ответ (текстовое сообщение)."""
    from services.grammar_ai import check_open_answer

    user_id = update.effective_user.id
    state = _grammar_state.get(user_id)
    if not state or state["phase"] != "open":
        return False  # не наше сообщение

    user_text = update.message.text.strip()
    topic = state["topic"]
    index = state["index"]
    q = topic["open"][index]

    await update.message.reply_text("⏳ Проверяю...")

    try:
        result = check_open_answer(q["question"], q["answer"], user_text, q.get("hint", ""))
    except Exception as e:
        await update.message.reply_text(f"❌ Ошибка проверки: {e}")
        state["index"] += 1
        await _send_next_question(update.message, user_id)
        return True

    if result.get("correct"):
        state["score"] += 1
        await update.message.reply_text(
            f"✅ *Верно!*\n_{result.get('explanation', '')}_",
            parse_mode="Markdown"
        )
    else:
        state["errors"].append({
            "question": q["question"],
            "user_answer": user_text,
            "correct": q["answer"]
        })
        await update.message.reply_text(
            f"❌ *Не совсем.*\nПравильно: *{q['answer']}*\n_{result.get('explanation', '')}_",
            parse_mode="Markdown"
        )

    state["index"] += 1
    await _send_next_question(update.message, user_id)
    return True


async def _finish_grammar(message, user_id: int):
    state = _grammar_state.pop(user_id, None)
    if not state:
        return

    topic = state["topic"]
    total = len(topic["quiz"]) + len(topic["open"])
    score = state["score"]
    errors = state["errors"]

    text = f"🏁 *Практика завершена!*\n\n📐 Тема: {topic['name']}\n⭐ Результат: *{score}/{total}*\n\n"

    if errors:
        text += "❌ *Разбор ошибок:*\n"
        for e in errors:
            text += f"• _{e['question']}_\n  Твой ответ: `{e['user_answer']}`\n  Правильно: `{e['correct']}`\n\n"
    else:
        text += "🎉 Отлично, ни одной ошибки!\n"

    await message.reply_text(text, reply_markup=_MENU_BTN, parse_mode="Markdown")


async def grammar_skip(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id

    state = _grammar_state.get(user_id)
    if not state:
        return

    phase = state["phase"]
    topic = state["topic"]

    if phase == "quiz":
        q = topic["quiz"][state["index"]]
        state["errors"].append({
            "question": q["question"],
            "user_answer": "—",
            "correct": q["answer"]
        })
        await query.message.reply_text(f"⏭ Пропущено. Правильный ответ: *{q['answer']}*", parse_mode="Markdown")
    elif phase == "open":
        q = topic["open"][state["index"]]
        state["errors"].append({
            "question": q["question"],
            "user_answer": "—",
            "correct": q["answer"]
        })
        await query.message.reply_text(f"⏭ Пропущено. Правильный ответ: *{q['answer']}*", parse_mode="Markdown")

    state["index"] += 1
    await _send_next_question(query.message, user_id)


async def grammar_stop(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id
    await _finish_grammar(query.message, user_id)


def get_grammar_handlers():
    return [
        CommandHandler("grammar", grammar_start),
        CallbackQueryHandler(grammar_choose_level, pattern=r"^grammar_level:"),
        CallbackQueryHandler(grammar_show_topic, pattern=r"^grammar_topic:"),
        CallbackQueryHandler(grammar_begin_practice, pattern=r"^grammar_start:"),
        CallbackQueryHandler(grammar_handle_answer, pattern=r"^grammar_answer:"),
        CallbackQueryHandler(grammar_skip, pattern=r"^grammar_skip$"),
        CallbackQueryHandler(grammar_stop, pattern=r"^grammar_stop$"),
    ]
