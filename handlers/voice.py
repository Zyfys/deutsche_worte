import os
import tempfile
from telegram import Update
from telegram.ext import ContextTypes
from database import ensure_user, get_active_session
from services.whisper import download_and_transcribe


async def handle_voice(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    ensure_user(user.id, user.username)

    await update.message.reply_text("🎤 Распознаю речь...")

    # Скачиваем голосовое сообщение
    voice = update.message.voice
    voice_file = await context.bot.get_file(voice.file_id)

    tmp = tempfile.NamedTemporaryFile(delete=False, suffix=".oga")
    tmp.close()

    try:
        text = await download_and_transcribe(voice_file, tmp.path if hasattr(tmp, 'path') else tmp.name)
    except RuntimeError as e:
        await update.message.reply_text(f"❌ {e}\n\nДобавь OPENAI_API_KEY в .env для голосовых сообщений.")
        return
    except Exception as e:
        await update.message.reply_text(f"❌ Не удалось распознать речь: {e}")
        return
    finally:
        try:
            os.unlink(tmp.name)
        except OSError:
            pass

    if not text:
        await update.message.reply_text("❌ Речь не распознана. Попробуй ещё раз.")
        return

    # Маршрутизация: есть активная практика — туда, иначе — поиск слова
    session = get_active_session(user.id)

    # Открытое задание по грамматике
    from handlers.grammar import grammar_handle_open, _grammar_state
    if user.id in _grammar_state and _grammar_state[user.id].get("phase") == "open":
        await update.message.reply_text(f'🎤 Распознано: "{text}"')
        # подменяем текст сообщения и передаём в grammar
        update.message.text = text
        await grammar_handle_open(update, context)
        return

    if session:
        from handlers.practice import process_practice_input
        await process_practice_input(update, context, text, recognized_from_voice=True)
    else:
        # Показываем что распознали и ищем слово
        await update.message.reply_text(f'🎤 Распознано: *"{text}"*', parse_mode="Markdown")
        from services.gemini import lookup_word
        from services.word_service import format_lookup_message
        try:
            data = lookup_word(text)
            msg = format_lookup_message(data)
            await update.message.reply_text(msg, parse_mode="Markdown")
        except Exception as e:
            await update.message.reply_text(f"❌ Не удалось найти слово: {e}")
