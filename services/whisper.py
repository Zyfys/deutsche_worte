import os
import tempfile
from openai import OpenAI
from config import OPENAI_API_KEY

_client = OpenAI(api_key=OPENAI_API_KEY) if OPENAI_API_KEY else None


def transcribe_voice(ogg_path: str) -> str:
    """Конвертирует OGG-файл из Telegram в текст через OpenAI Whisper."""
    if not _client:
        raise RuntimeError("OPENAI_API_KEY не установлен в .env")

    # Telegram присылает .oga (OGG Opus) — Whisper принимает его напрямую
    with open(ogg_path, "rb") as f:
        result = _client.audio.transcriptions.create(
            model="whisper-1",
            file=f,
            language="de",  # Подсказываем что речь немецкая — точнее распознаёт
        )
    return result.text.strip()


async def download_and_transcribe(voice_file, download_path: str) -> str:
    """Скачивает голосовое из Telegram и транскрибирует."""
    await voice_file.download_to_drive(download_path)
    return transcribe_voice(download_path)
