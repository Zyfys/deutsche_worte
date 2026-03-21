# German Word Bot — CLAUDE.md

## О проекте

Telegram-бот для изучения немецкого языка. Отправляет слово дня, проводит викторины и экзамены, поддерживает разговорную и письменную практику, симулятор экзамена Goethe, грамматику и голосовые сообщения.

## Стек технологий

| Компонент | Технология |
|-----------|-----------|
| Язык | Python 3.11+ |
| Telegram | python-telegram-bot 20.7 |
| База данных | PostgreSQL + psycopg2 |
| AI | Google Gemini API (google-generativeai) |
| TTS | gTTS |
| STT | OpenAI Whisper (опционально) |
| Расписание | APScheduler 3.x |
| PDF | pdfplumber |
| Конфиг | python-dotenv |

## Команды запуска

```bash
# Запуск бота
cd german-bot
python bot.py

# Установка зависимостей
pip install -r requirements.txt
```

## Архитектура папок

```
german-bot/
├── bot.py                    # Точка входа, регистрация хендлеров
├── config.py                 # Конфигурация из .env
├── database.py               # Работа с PostgreSQL (init_db, CRUD)
├── scheduler.py              # APScheduler: слово дня, викторины, экзамены
├── handlers/
│   ├── commands.py           # /start, /help, /stats, /word_now, menu_callback
│   ├── messages.py           # Роутинг текстовых сообщений + поиск слов
│   ├── quiz.py               # Викторина и ежемесячный экзамен
│   ├── practice.py           # Разговорная практика (A2–C1)
│   ├── writing.py            # Письменная практика с оценкой
│   ├── goethe_exam.py        # Симулятор экзамена Goethe
│   ├── grammar.py            # Грамматика по темам (A1–B1)
│   └── voice.py              # Голосовые сообщения
├── services/
│   ├── gemini.py             # Gemini API клиент
│   ├── word_service.py       # Форматирование слов
│   ├── grammar_ai.py         # AI для грамматики
│   ├── practice_ai.py        # AI для практики
│   ├── tts.py                # Text-to-Speech
│   ├── whisper.py            # Speech-to-Text
│   └── pdf_parser.py         # Парсинг PDF
├── data/
│   ├── goethe_wordlist_b1.txt
│   ├── grammar.json
│   ├── scenarios.json
│   └── exam_tasks*.json
├── .env                      # Секреты (не в git)
├── .env.example
├── .gitignore
├── requirements.txt
├── TODO.md                   # Текущие задачи
├── LESSONS.md                # Уроки и заметки
└── PLAN.md                   # План проекта
```

## Переменные окружения (.env)

```
TELEGRAM_BOT_TOKEN=...
GEMINI_API_KEY=...
DATABASE_URL=postgresql://postgres:password@localhost:5432/german_bot
OPENAI_API_KEY=...  # опционально, для Whisper
```

## Расписание (UTC, config.py)

- Слово дня: 08:00 UTC (11:00 МСК)
- Еженедельная викторина: воскресенье 07:00 UTC (10:00 МСК)
- Ежемесячный экзамен: 1-е число 07:00 UTC (10:00 МСК)

## Стиль кода

- Хендлеры регистрируются через get_*_handlers() функции
- Конфиг только через config.py, никаких os.getenv напрямую
- Логирование через стандартный logging
- Асинхронный код (async/await)

## Правила работы

- Сначала план, потом код — никогда наоборот
- Перед большой задачей: декомпозируй на шаги, покажи план
- После каждой фичи: обнови TODO.md
- Если узнал что-то важное: запиши в LESSONS.md
- /compact когда контекст ~50% заполнен
- /clear при переключении на новую несвязанную задачу
- Коммиты после каждой рабочей фичи, не в конце дня

## Ссылки

- [TODO.md](TODO.md) — текущие задачи
- [LESSONS.md](LESSONS.md) — уроки и заметки
- [PLAN.md](PLAN.md) — план проекта
