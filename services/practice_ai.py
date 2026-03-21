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


def continue_conversation(scenario: dict, level: str, history: list, user_message: str) -> dict:
    """
    Продолжает ролевой диалог как персонаж сценария.
    Одновременно даёт feedback по ошибкам пользователя.

    Возвращает: {"bot_reply": str, "feedback": str, "errors": list[str]}
    """
    history_text = "\n".join(
        f"{'Ты' if m['role'] == 'user' else scenario['role']}: {m['text']}"
        for m in history[-10:]
    )

    prompt = f"""Ты — языковой тренер немецкого языка и одновременно играешь роль: {scenario['role']}.
Уровень ученика: {level}
Сценарий: {scenario.get('description', scenario['name'])}

История диалога:
{history_text}
Ученик: {user_message}

Твоя задача:
1. Продолжи диалог В РОЛИ {scenario['role']} — ответь на немецком языке, соответствующем уровню {level}
2. Если ученик допустил грамматические или лексические ошибки — укажи их кратко на русском
3. Если ошибок нет — напиши "Отлично, ошибок нет!"

Верни ТОЛЬКО валидный JSON без markdown:
{{
  "bot_reply": "ответ на немецком от лица {scenario['role']}",
  "feedback": "краткий feedback на русском (ошибки или похвала)",
  "errors": [{{"wrong": "неверный вариант", "correct": "правильный вариант"}}]
}}"""

    return _parse_json(_call(prompt))


def evaluate_writing(level: str, task: dict, user_text: str) -> dict:
    """
    Оценивает письменную работу по критериям Goethe.

    Возвращает: {"score": "7/10", "criteria": {...}, "corrections": [...], "corrected_text": str}
    """
    prompt = f"""Ты — экзаменатор Goethe-Institut. Оцени письменную работу ученика.

Уровень: {level}
Задание: {task['instruction']}

Работа ученика:
{user_text}

Оцени по критериям Goethe:
- Aufgabe (выполнение задания): выполнено ли задание, раскрыты ли все пункты
- Kohärenz (связность): логика и структура текста
- Ausdruck (лексика): разнообразие и точность лексики
- Korrektheit (грамматика): грамматические ошибки

Верни ТОЛЬКО валидный JSON без markdown:
{{
  "score": "число от 0 до 10",
  "criteria": {{
    "Aufgabe": "оценка и комментарий",
    "Kohärenz": "оценка и комментарий",
    "Ausdruck": "оценка и комментарий",
    "Korrektheit": "оценка и комментарий"
  }},
  "corrections": [{{"wrong": "неверный вариант", "correct": "правильный вариант"}}],
  "corrected_text": "исправленная версия текста на немецком",
  "tip": "совет для улучшения на русском"
}}"""

    return _parse_json(_call(prompt))


def generate_writing_task(level: str) -> dict:
    """Генерирует новое письменное задание по уровню."""
    prompt = f"""Создай письменное задание для экзамена Goethe уровня {level}.

Верни ТОЛЬКО валидный JSON без markdown:
{{
  "title": "название задания",
  "instruction": "полное задание на русском с чёткими инструкциями",
  "min_words": число,
  "max_words": число,
  "tips": ["подсказка 1", "подсказка 2"]
}}"""

    return _parse_json(_call(prompt))


def evaluate_goethe_sprechen(level: str, scenario_description: str,
                              user_text: str) -> dict:
    """
    Оценивает устное высказывание (Sprechen) по критериям Goethe.

    Возвращает: {"score": str, "criteria": dict, "tip": str}
    """
    prompt = f"""Ты — экзаменатор Goethe-Institut (Sprechen, уровень {level}).

Задание: {scenario_description}

Высказывание ученика (распознанная речь):
{user_text}

Оцени по 4 критериям Goethe Sprechen:
- Aufgabe: выполнение коммуникативной задачи
- Kohärenz: связность и логика высказывания
- Ausdruck: лексическое разнообразие
- Korrektheit: грамматика и произношение (по тексту)

Верни ТОЛЬКО валидный JSON без markdown:
{{
  "score": "X/20",
  "criteria": {{
    "Aufgabe": {{"points": число, "comment": "комментарий"}},
    "Kohärenz": {{"points": число, "comment": "комментарий"}},
    "Ausdruck": {{"points": число, "comment": "комментарий"}},
    "Korrektheit": {{"points": число, "comment": "комментарий"}}
  }},
  "tip": "главный совет на русском"
}}"""

    return _parse_json(_call(prompt))


def summarize_conversation(scenario: dict, level: str, messages: list) -> dict:
    """Итоговая оценка всего диалога."""
    dialogue = "\n".join(
        f"{'Ученик' if m['role'] == 'user' else scenario['role']}: {m['text']}"
        for m in messages
    )

    prompt = f"""Оцени разговорную практику ученика уровня {level}.
Сценарий: {scenario['name']}

Диалог:
{dialogue}

Верни ТОЛЬКО валидный JSON без markdown:
{{
  "overall_score": "X/10",
  "strengths": ["сильная сторона 1", "сильная сторона 2"],
  "weaknesses": ["слабое место 1", "слабое место 2"],
  "frequent_errors": [{{"wrong": "неверный вариант", "correct": "правильный вариант"}}],
  "recommendation": "общая рекомендация на русском"
}}"""

    return _parse_json(_call(prompt))


def _parse_json(text: str) -> dict:
    text = text.strip()
    if text.startswith("```"):
        lines = text.split("\n")
        text = "\n".join(lines[1:-1] if lines[-1].strip() == "```" else lines[1:])
    return json.loads(text)
