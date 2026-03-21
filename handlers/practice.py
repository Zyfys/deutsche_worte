import json
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes, CommandHandler, CallbackQueryHandler
from database import (
    ensure_user, get_active_session, create_practice_session,
    append_practice_message, finish_practice_session,
    get_user_level
)
from services.practice_ai import continue_conversation, summarize_conversation

# Загрузка сценариев
with open("data/scenarios.json", encoding="utf-8") as f:
    SCENARIOS = json.load(f)

LEVELS = ["A2", "B1", "B2", "C1"]

_STOP_BTN = InlineKeyboardMarkup([[InlineKeyboardButton("🛑 Завершить и получить оценку", callback_data="practice_stop")]])
_MENU_BTN = InlineKeyboardMarkup([[InlineKeyboardButton("🏠 Главное меню", callback_data="menu:main")]])


async def practice_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    ensure_user(user.id, user.username)

    session = get_active_session(user.id)
    if session:
        await update.message.reply_text(
            "⚠️ У тебя уже идёт практика!\n"
            "Напиши /stop чтобы завершить текущую, или продолжай отвечать."
        )
        return

    buttons = [[InlineKeyboardButton(lvl, callback_data=f"practice_level:{lvl}")]
               for lvl in LEVELS]
    await update.message.reply_text(
        "🎭 *Разговорная практика*\n\n"
        "Выбери уровень сложности:",
        reply_markup=InlineKeyboardMarkup(buttons),
        parse_mode="Markdown"
    )


async def practice_choose_level(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    level = query.data.split(":")[1]

    scenarios = SCENARIOS.get(level, [])
    if not scenarios:
        await query.edit_message_text(f"Для уровня {level} пока нет сценариев.")
        return

    btns = [InlineKeyboardButton(s["name"], callback_data=f"practice_scenario:{level}:{s['id']}") for s in scenarios]
    buttons = [btns[i:i+2] for i in range(0, len(btns), 2)]
    await query.edit_message_text(
        f"📋 Уровень *{level}* — выбери сценарий:",
        reply_markup=InlineKeyboardMarkup(buttons),
        parse_mode="Markdown"
    )


async def practice_choose_scenario(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    _, level, scenario_id = query.data.split(":")
    scenarios = SCENARIOS.get(level, [])
    scenario = next((s for s in scenarios if s["id"] == scenario_id), None)

    if not scenario:
        await query.edit_message_text("❌ Сценарий не найден.")
        return

    user_id = query.from_user.id
    session_id = create_practice_session(user_id, "conversation", level, scenario_id)
    append_practice_message(session_id, "bot", scenario["starter"])

    await query.edit_message_text(
        f"🎭 *Сценарий:* {scenario['name']}\n"
        f"👤 *Я играю роль:* {scenario['role']} ({scenario['role_ru']})\n\n"
        f"_{scenario['description']}_\n\n"
        f"──────────────────\n"
        f"*{scenario['role']}:* {scenario['starter']}\n\n"
        f"──────────────────\n"
        f"💬 Отвечай текстом или голосовым сообщением.",
        reply_markup=_STOP_BTN,
        parse_mode="Markdown"
    )


async def process_practice_input(update: Update, context: ContextTypes.DEFAULT_TYPE,
                                  user_text: str, recognized_from_voice: bool = False):
    user_id = update.effective_user.id
    session = get_active_session(user_id)

    if not session:
        return

    level = session["level"]
    scenario_id = session["scenario"]
    scenarios = SCENARIOS.get(level, [])
    scenario = next((s for s in scenarios if s["id"] == scenario_id), None)

    if not scenario:
        return

    append_practice_message(session["id"], "user", user_text)

    prefix = f'🎤 *Распознано:* "{user_text}"\n\n' if recognized_from_voice else ""
    messages = session["messages"] if isinstance(session["messages"], list) else []

    try:
        result = continue_conversation(scenario, level, messages, user_text)
    except Exception as e:
        await update.message.reply_text(f"❌ Ошибка AI: {e}")
        return

    bot_reply = result.get("bot_reply", "...")
    feedback = result.get("feedback", "")
    errors = result.get("errors", [])

    append_practice_message(session["id"], "bot", bot_reply, feedback)

    text = f"{prefix}*{scenario['role']}:* {bot_reply}\n\n"

    if errors:
        text += "📝 *Ошибки:*\n"
        for e in errors:
            if isinstance(e, dict):
                text += f"_{e.get('wrong', '')}_ ➡️ *{e.get('correct', '')}*\n"
            else:
                text += f"• {e}\n"
    elif feedback:
        text += f"✅ {feedback}"

    await update.message.reply_text(text, parse_mode="Markdown", reply_markup=_STOP_BTN)


async def practice_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    session = get_active_session(user_id)
    if not session:
        return
    await process_practice_input(update, context, update.message.text)


async def _finish_conversation(target, session, user_id: int):
    """Общая логика завершения разговорной практики. target — message объект для ответа."""
    level = session["level"]
    scenario_id = session["scenario"]
    scenarios = SCENARIOS.get(level, [])
    scenario = next((s for s in scenarios if s["id"] == scenario_id), None)
    messages = session["messages"] if isinstance(session["messages"], list) else []

    try:
        evaluation = summarize_conversation(scenario, level, messages)
    except Exception as e:
        evaluation = {"overall_score": "—", "recommendation": str(e)}

    finish_practice_session(session["id"], user_id, evaluation)

    score = evaluation.get("overall_score", "—")
    strengths = evaluation.get("strengths", [])
    weaknesses = evaluation.get("weaknesses", [])
    errors = evaluation.get("frequent_errors", [])
    rec = evaluation.get("recommendation", "")

    text = f"🏁 *Практика завершена!*\n\n📊 Оценка: *{score}*\n\n"

    if strengths:
        text += "✅ *Сильные стороны:*\n" + "\n".join(f"• {s}" for s in strengths) + "\n\n"
    if weaknesses:
        text += "📌 *Над чем поработать:*\n" + "\n".join(f"• {w}" for w in weaknesses) + "\n\n"
    if errors:
        text += "❌ *Частые ошибки:*\n"
        for e in errors:
            if isinstance(e, dict):
                text += f"_{e.get('wrong', '')}_ ➡️ *{e.get('correct', '')}*\n"
            else:
                text += f"• {e}\n"
        text += "\n"
    if rec:
        text += f"💡 {rec}"

    await target.reply_text(text, parse_mode="Markdown", reply_markup=_MENU_BTN)


async def practice_stop(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """/stop — завершает любой тип активной сессии."""
    user_id = update.effective_user.id
    session = get_active_session(user_id)

    if not session:
        await update.message.reply_text("Нет активной практики. Начни с /practice")
        return

    stype = session.get("session_type", "")

    if stype == "conversation":
        await update.message.reply_text("⏳ Анализирую диалог...")
        await _finish_conversation(update.message, session, user_id)

    elif stype == "writing":
        finish_practice_session(session["id"], user_id, {})
        await update.message.reply_text(
            "✅ Письменная практика отменена.",
            reply_markup=_MENU_BTN
        )

    elif stype == "goethe_exam":
        finish_practice_session(session["id"], user_id, {})
        await update.message.reply_text(
            "✅ Экзамен прерван.",
            reply_markup=_MENU_BTN
        )

    else:
        finish_practice_session(session["id"], user_id, {})
        await update.message.reply_text("✅ Сессия завершена.", reply_markup=_MENU_BTN)


async def practice_stop_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    await query.edit_message_reply_markup(reply_markup=None)

    user_id = query.from_user.id
    session = get_active_session(user_id)

    if not session:
        await query.message.reply_text("Нет активной практики.", reply_markup=_MENU_BTN)
        return

    await query.message.reply_text("⏳ Анализирую диалог...")
    await _finish_conversation(query.message, session, user_id)


def get_practice_handlers():
    return [
        CommandHandler("practice", practice_start),
        CommandHandler("stop", practice_stop),
        CallbackQueryHandler(practice_choose_level, pattern=r"^practice_level:"),
        CallbackQueryHandler(practice_choose_scenario, pattern=r"^practice_scenario:"),
        CallbackQueryHandler(practice_stop_callback, pattern=r"^practice_stop$"),
    ]
