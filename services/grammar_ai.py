import json
from groq import Groq
from config import GROQ_API_KEY, GROQ_MODEL

_client = Groq(api_key=GROQ_API_KEY)
_MODEL = GROQ_MODEL


def _call(prompt: str) -> str:
    response = _client.chat.completions.create(
        model=_MODEL,
        messages=[{"role": "user", "content": prompt}],
    )
    return response.choices[0].message.content


def check_open_answer(question: str, correct: str, user_answer: str, hint: str = "") -> dict:
    """
    Проверяет открытый ответ по грамматике.
    Возвращает: {"correct": bool, "explanation": str}
    """
    prompt = f"""Ты — учитель немецкого языка. Проверь ответ ученика на упражнение по грамматике.

Задание: {question}
Правильный ответ: {correct}
Ответ ученика: {user_answer}
Подсказка: {hint}

Оцени ответ:
- Считай правильным если смысл и грамматика верны, допускай незначительные опечатки
- Если неверно — объясни ошибку кратко по-русски (1-2 предложения)
- Если верно — напиши краткое подтверждение

Верни ТОЛЬКО валидный JSON без markdown:
{{"correct": true/false, "explanation": "краткое объяснение на русском"}}"""

    text = _call(prompt).strip()
    if text.startswith("```"):
        lines = text.split("\n")
        text = "\n".join(lines[1:-1] if lines[-1].strip() == "```" else lines[1:])
    return json.loads(text)
