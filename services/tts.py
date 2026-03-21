import os
import tempfile
from gtts import gTTS


def speak(text: str, lang: str = "de") -> str:
    """Преобразует текст в речь. Возвращает путь к временному MP3 файлу."""
    tts = gTTS(text=text, lang=lang, slow=False)
    tmp = tempfile.NamedTemporaryFile(delete=False, suffix=".mp3")
    tts.save(tmp.name)
    return tmp.name


def speak_slow(text: str) -> str:
    """Медленное произношение — для изучения."""
    tts = gTTS(text=text, lang="de", slow=True)
    tmp = tempfile.NamedTemporaryFile(delete=False, suffix=".mp3")
    tts.save(tmp.name)
    return tmp.name


def cleanup(path: str):
    """Удалить временный файл после отправки."""
    try:
        os.unlink(path)
    except OSError:
        pass
