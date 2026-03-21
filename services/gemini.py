import json
import os
import random
from groq import Groq
from config import GROQ_API_KEY, GROQ_MODEL

_client = Groq(api_key=GROQ_API_KEY)
_MODEL = GROQ_MODEL

_WORD_SCHEMA = """{
  "word": "строка — само немецкое слово",
  "article": "der/die/das или null для глаголов/прилагательных",
  "part_of_speech": "verb/noun/adjective/adverb",
  "präteritum": "форма претерита (только для глаголов, иначе null)",
  "perfekt": "форма перфекта (только для глаголов, иначе null)",
  "plural": "форма множественного числа (только для существительных, иначе null)",
  "translation": "перевод на русский",
  "synonyms": [{"word": "синоним", "translation": "перевод"}],
  "antonyms": [{"word": "антоним", "translation": "перевод"}],
  "examples": ["пример 1 на немецком", "пример 2 на немецком"],
  "explanation": "краткое пояснение на русском — как и когда используется слово"
}"""

# Загрузка списка слов Goethe B1 при старте
_GOETHE_WORDS: list[str] = []

def _load_goethe_wordlist():
    path = os.path.join(os.path.dirname(__file__), "..", "data", "goethe_wordlist_b1.txt")
    try:
        with open(path, encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith("#"):
                    _GOETHE_WORDS.append(line)
    except FileNotFoundError:
        pass

_load_goethe_wordlist()


def _call(prompt: str) -> str:
    response = _client.chat.completions.create(
        model=_MODEL,
        messages=[{"role": "user", "content": prompt}],
    )
    return response.choices[0].message.content


def generate_daily_word(used_words: list[str]) -> dict:
    exclude = set(used_words[-100:]) if used_words else set()
    exclude_str = ", ".join(list(exclude)[:50]) if exclude else "нет"

    suggestion = ""
    if _GOETHE_WORDS:
        available = [w for w in _GOETHE_WORDS if w not in exclude]
        if available:
            pick = random.choice(available)
            suggestion = f"\nПредпочтительно используй слово из списка Goethe B1, например: «{pick}». Если оно уже в исключениях — выбери похожее по уровню."

    prompt = f"""Ты помогаешь учить немецкий язык. Сгенерируй одно немецкое слово уровня A2–B1.{suggestion}

Уже использованные слова (не повторяй): {exclude_str}

Верни ТОЛЬКО валидный JSON без markdown-блоков, строго по схеме:
{_WORD_SCHEMA}

Требования:
- Слово должно быть полезным и часто используемым (уровень A2–B1)
- Синонимов и антонимов по 1-2 штуки
- Примеров ровно 2
- Объяснение 1-2 предложения на русском"""

    return _parse_json(_call(prompt))


def lookup_word(word: str) -> dict:
    prompt = f"""Ты помогаешь учить немецкий язык. Дай подробную информацию о слове «{word}».

Верни ТОЛЬКО валидный JSON без markdown-блоков, строго по схеме:
{_WORD_SCHEMA}

Если слово не немецкое — всё равно заполни поля насколько возможно."""

    return _parse_json(_call(prompt))


def _parse_json(text: str) -> dict:
    text = text.strip()
    if text.startswith("```"):
        lines = text.split("\n")
        text = "\n".join(lines[1:-1] if lines[-1].strip() == "```" else lines[1:])
    return json.loads(text)
