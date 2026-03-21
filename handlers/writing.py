import json
import random
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes, CommandHandler, CallbackQueryHandler
from database import (
    ensure_user, get_active_session, create_practice_session,
    append_practice_message, finish_practice_session,
    get_user_level
)
from services.practice_ai import evaluate_writing, generate_writing_task

with open("data/exam_tasks.json", encoding="utf-8") as f:
    EXAM_TASKS = json.load(f)

LEVELS = ["A2", "B1", "B2", "C1"]

_pending_task: dict[int, dict] = {}

_CANCEL_BTN = InlineKeyboardMarkup([[InlineKeyboardButton("❌ Отменить задание", callback_data="writing_cancel")]])
_MENU_BTN   = InlineKeyboardMarkup([[InlineKeyboardButton("🏠 Главное меню", callback_data="menu:main")]])


async def writing_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    ensure_user(user.id, user.username)

    session = get_active_session(user.id)
    if session:
        await update.message.reply_text(
            "⚠️ У тебя уже идёт практика.\nНапиши /stop чтобы завершить."
        )
        return

    btns = [InlineKeyboardButton(lvl, callback_data=f"write_level:{lvl}") for lvl in LEVELS]
    buttons = [btns[i:i+2] for i in range(0, len(btns), 2)]
    await update.message.reply_text(
        "✍️ *Практика письма*\n\nВыбери уровень:",
        reply_markup=InlineKeyboardMarkup(buttons),
        parse_mode="Markdown"
    )


async def writing_choose_level(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    level = query.data.split(":")[1]
    user_id = query.from_user.id

    level_tasks = EXAM_TASKS.get(level, {}).get("schreiben", [])
    if level_tasks:
        task = random.choice(level_tasks)
    else:
        await query.edit_message_text("⏳ Генерирую задание...")
        try:
            task = generate_writing_task(level)
        except Exception as e:
            await query.edit_message_text(f"❌ Ошибка: {e}")
            return

    _pending_task[user_id] = {"task": task, "level": level}

    session_id = create_practice_session(user_id, "writing", level, "schreiben")
    append_practice_message(session_id, "bot", task["instruction"])

    word_range = ""
    if task.get("min_words") and task.get("max_words"):
        word_range = f"\n📏 Объём: {task['min_words']}–{task['max_words']} слов"

    await query.edit_message_text(
        f"✍️ *Задание ({level})*\n\n"
        f"{task['instruction']}{word_range}\n\n"
        f"──────────────────\n"
        f"Напиши свой текст одним сообщением.",
        reply_markup=_CANCEL_BTN,
        parse_mode="Markdown"
    )


async def writing_cancel_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    await query.edit_message_reply_markup(reply_markup=None)

    user_id = query.from_user.id
    session = get_active_session(user_id)
    if session and session["session_type"] == "writing":
        finish_practice_session(session["id"], user_id, {})
    _pending_task.pop(user_id, None)

    await query.message.reply_text("✅ Задание отменено.", reply_markup=_MENU_BTN)


async def writing_submit(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    session = get_active_session(user_id)

    if not session or session["session_type"] != "writing":
        return

    pending = _pending_task.get(user_id)
    if not pending:
        return

    user_text = update.message.text
    level = pending["level"]
    task = pending["task"]

    await update.message.reply_text("⏳ Проверяю работу...")

    try:
        result = evaluate_writing(level, task, user_text)
    except Exception as e:
        await update.message.reply_text(f"❌ Ошибка оценки: {e}")
        return

    append_practice_message(session["id"], "user", user_text)
    finish_practice_session(session["id"], user_id, result)
    del _pending_task[user_id]

    score = result.get("score", "—")
    criteria = result.get("criteria", {})
    corrections = result.get("corrections", [])
    corrected = result.get("corrected_text", "")
    tip = result.get("tip", "")

    text = f"📊 *Оценка: {score}/10*\n\n"

    for crit, comment in criteria.items():
        text += f"*{crit}:* {comment}\n"

    if corrections:
        text += "\n✏️ *Исправления:*\n"
        for c in corrections[:5]:
            if isinstance(c, dict):
                text += f"_{c.get('wrong', '')}_ ➡️ *{c.get('correct', '')}*\n"
            else:
                text += f"• {c}\n"

    if corrected:
        text += f"\n\n📝 *Исправленная версия:*\n_{corrected}_"

    if tip:
        text += f"\n\n💡 {tip}"

    await update.message.reply_text(text, parse_mode="Markdown", reply_markup=_MENU_BTN)


def get_writing_handlers():
    return [
        CommandHandler("write", writing_start),
        CallbackQueryHandler(writing_choose_level, pattern=r"^write_level:"),
        CallbackQueryHandler(writing_cancel_callback, pattern=r"^writing_cancel$"),
    ]
