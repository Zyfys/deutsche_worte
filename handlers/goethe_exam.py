import json
import random
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes, CommandHandler, CallbackQueryHandler
from database import (
    ensure_user, get_active_session, create_practice_session,
    append_practice_message, finish_practice_session, get_user_level
)
from services.practice_ai import evaluate_goethe_sprechen, evaluate_writing

with open("data/exam_tasks.json", encoding="utf-8") as f:
    EXAM_TASKS = json.load(f)

LEVELS = ["A2", "B1", "B2", "C1"]
SECTIONS = [("sprechen", "🎙️ Sprechen"), ("schreiben", "✍️ Schreiben")]

_exam_state: dict[int, dict] = {}

_MENU_BTN = InlineKeyboardMarkup([[InlineKeyboardButton("🏠 Главное меню", callback_data="menu:main")]])
_TASK_BTNS = InlineKeyboardMarkup([
    [InlineKeyboardButton("⏭ Пропустить секцию", callback_data="goethe_skip")],
    [InlineKeyboardButton("🛑 Завершить экзамен",  callback_data="goethe_stop")],
])


async def goethe_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    ensure_user(user.id, user.username)

    session = get_active_session(user.id)
    if session:
        await update.message.reply_text("⚠️ Завершите текущую практику (/stop)")
        return

    btns = [InlineKeyboardButton(lvl, callback_data=f"goethe_level:{lvl}") for lvl in LEVELS]
    buttons = [btns[i:i+2] for i in range(0, len(btns), 2)]
    await update.message.reply_text(
        "📋 *Симулятор Goethe-Zertifikat*\n\nВыбери уровень:",
        reply_markup=InlineKeyboardMarkup(buttons),
        parse_mode="Markdown"
    )


async def goethe_choose_level(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    level = query.data.split(":")[1]

    buttons = [
        [InlineKeyboardButton(label, callback_data=f"goethe_section:{level}:{sec}")]
        for sec, label in SECTIONS
    ] + [[InlineKeyboardButton("📚 Полный экзамен", callback_data=f"goethe_section:{level}:full")]]

    await query.edit_message_text(
        f"📋 *Goethe {level}* — выбери секцию:",
        reply_markup=InlineKeyboardMarkup(buttons),
        parse_mode="Markdown"
    )


async def goethe_choose_section(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    parts = query.data.split(":")
    level, section = parts[1], parts[2]
    user_id = query.from_user.id

    level_tasks = EXAM_TASKS.get(level, {})

    if section == "full":
        sections_to_do = [s for s, _ in SECTIONS if s in level_tasks]
    else:
        sections_to_do = [section] if section in level_tasks else []

    if not sections_to_do:
        await query.edit_message_text(f"❌ Для уровня {level} нет заданий для этой секции.")
        return

    _exam_state[user_id] = {
        "level": level,
        "sections": sections_to_do,
        "current_section_idx": 0,
        "results": {}
    }

    session_id = create_practice_session(user_id, "goethe_exam", level, section)
    _exam_state[user_id]["session_id"] = session_id

    await query.edit_message_text(
        f"📋 *Экзамен Goethe {level}* начинается!\n\n"
        f"Секций: {len(sections_to_do)}\n"
        f"Используй кнопки под заданием для управления."
    )

    await _send_next_section(user_id, context.bot, _exam_state[user_id])


async def _send_next_section(user_id: int, bot, state: dict):
    idx = state["current_section_idx"]
    if idx >= len(state["sections"]):
        await _finish_exam(user_id, bot, state)
        return

    section = state["sections"][idx]
    level = state["level"]
    tasks = EXAM_TASKS.get(level, {}).get(section, [])

    if not tasks:
        state["current_section_idx"] += 1
        await _send_next_section(user_id, bot, state)
        return

    task = random.choice(tasks)
    state["current_task"] = task
    state["current_section"] = section

    if section == "sprechen":
        msg = (
            f"🎙️ *Sprechen — Задание {idx + 1}*\n\n"
            f"{task['instruction']}\n\n"
            f"⏱ Время: ~{task.get('time_seconds', 120) // 60} мин\n\n"
            f"Запиши голосовое сообщение или напиши текст."
        )
    else:
        word_range = ""
        if task.get("min_words"):
            word_range = f"\n📏 Объём: {task['min_words']}–{task['max_words']} слов"
        msg = (
            f"✍️ *Schreiben — Задание {idx + 1}*\n\n"
            f"{task['instruction']}{word_range}\n\n"
            f"Напиши свой текст одним сообщением."
        )

    await bot.send_message(user_id, msg, parse_mode="Markdown", reply_markup=_TASK_BTNS)


async def goethe_answer(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    state = _exam_state.get(user_id)

    if not state:
        return

    session = get_active_session(user_id)
    if not session or session["session_type"] != "goethe_exam":
        return

    user_text = update.message.text
    section = state.get("current_section")
    task = state.get("current_task")
    level = state["level"]

    if not section or not task:
        return

    await update.message.reply_text("⏳ Оцениваю...")

    try:
        if section == "sprechen":
            result = evaluate_goethe_sprechen(level, task["instruction"], user_text)
        else:
            result = evaluate_writing(level, task, user_text)
    except Exception as e:
        await update.message.reply_text(f"❌ Ошибка оценки: {e}")
        return

    state["results"][section] = result
    append_practice_message(
        state["session_id"], "user", user_text,
        json.dumps(result, ensure_ascii=False)
    )

    if section == "sprechen":
        score = result.get("score", "—")
        tip = result.get("tip", "")
        criteria = result.get("criteria", {})
        text = f"📊 *Sprechen: {score}*\n\n"
        for crit, data in criteria.items():
            if isinstance(data, dict):
                text += f"*{crit}:* {data.get('points', '—')} — {data.get('comment', '')}\n"
        if tip:
            text += f"\n💡 {tip}"
    else:
        score = result.get("score", "—")
        text = f"📊 *Schreiben: {score}/10*\n"
        corrections = result.get("corrections", [])
        if corrections:
            text += "\n✏️ *Исправления:*\n" + "\n".join(f"• {c}" for c in corrections[:3])

    await update.message.reply_text(text, parse_mode="Markdown")

    state["current_section_idx"] += 1
    await _send_next_section(user_id, context.bot, state)


async def goethe_skip_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Кнопка ⏭ Пропустить секцию."""
    query = update.callback_query
    await query.answer()
    await query.edit_message_reply_markup(reply_markup=None)

    user_id = query.from_user.id
    state = _exam_state.get(user_id)
    if not state:
        return

    state["current_section_idx"] += 1
    await _send_next_section(user_id, context.bot, state)


async def goethe_stop_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Кнопка 🛑 Завершить экзамен."""
    query = update.callback_query
    await query.answer()
    await query.edit_message_reply_markup(reply_markup=None)

    user_id = query.from_user.id
    state = _exam_state.pop(user_id, None)

    session = get_active_session(user_id)
    if session:
        finish_practice_session(session["id"], user_id, state.get("results", {}) if state else {})

    await query.message.reply_text("✅ Экзамен завершён досрочно.", reply_markup=_MENU_BTN)


async def _finish_exam(user_id: int, bot, state: dict):
    results = state.get("results", {})
    finish_practice_session(state["session_id"], user_id, results)
    del _exam_state[user_id]

    text = "🎓 *Экзамен завершён!*\n\n📊 *Итоговые результаты:*\n\n"
    for section, result in results.items():
        if section == "sprechen":
            text += f"🎙️ Sprechen: *{result.get('score', '—')}*\n"
        else:
            text += f"✍️ Schreiben: *{result.get('score', '—')}/10*\n"

    text += "\nПродолжай тренироваться! 💪"
    await bot.send_message(user_id, text, parse_mode="Markdown",
                           reply_markup=_MENU_BTN)


async def goethe_next(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """/next — пропустить текущую секцию."""
    user_id = update.effective_user.id
    state = _exam_state.get(user_id)
    if not state:
        await update.message.reply_text("Нет активного экзамена.")
        return
    state["current_section_idx"] += 1
    await _send_next_section(user_id, context.bot, state)


def get_goethe_handlers():
    return [
        CommandHandler("goethe", goethe_start),
        CommandHandler("next", goethe_next),
        CallbackQueryHandler(goethe_choose_level,   pattern=r"^goethe_level:"),
        CallbackQueryHandler(goethe_choose_section, pattern=r"^goethe_section:"),
        CallbackQueryHandler(goethe_skip_callback,  pattern=r"^goethe_skip$"),
        CallbackQueryHandler(goethe_stop_callback,  pattern=r"^goethe_stop$"),
    ]
