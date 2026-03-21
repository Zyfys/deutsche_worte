# 🇩🇪 German Word Bot

Telegram-бот для изучения немецкого языка. Каждый день — новое слово, еженедельные викторины, ежемесячные экзамены.

## Возможности

- 📅 **Слово дня** — каждый день в 9:00 МСК приходит новое немецкое слово с переводом, формами, синонимами, антонимами и примерами
- 🔍 **Поиск слов** — напиши любое немецкое слово, бот даст перевод и примеры
- 🏆 **Викторина** — каждое воскресенье проверка слов за неделю
- 📋 **Экзамен** — 1-го числа каждого месяца экзамен по словам за месяц
- 📊 **Статистика** — прогресс и результаты

## Установка

### 1. Получи токены

- **Telegram Bot Token** — создай бота через [@BotFather](https://t.me/BotFather)
- **Gemini API Key** — получи бесплатно на [Google AI Studio](https://aistudio.google.com/apikey)

### 2. Установи PostgreSQL

Скачай с [postgresql.org](https://www.postgresql.org/download/) и создай базу данных:

```bash
createdb german_bot
```

### 3. Настрой окружение

```bash
cd german-bot
cp .env.example .env
```

Открой `.env` и заполни:

```
TELEGRAM_BOT_TOKEN=your_token_here
GEMINI_API_KEY=your_gemini_key_here
DATABASE_URL=postgresql://postgres:your_password@localhost:5432/german_bot
```

### 4. Установи зависимости

```bash
pip install -r requirements.txt
```

### 5. Запусти бота

```bash
python bot.py
```

## Команды бота

| Команда | Описание |
|---------|----------|
| `/start` | Начало работы |
| `/help` | Помощь |
| `/stats` | Статистика и результаты |
| `/word_now` | Получить слово прямо сейчас |
| `/quiz_now` | Запустить викторину сейчас |
| `/exam_now` | Запустить экзамен сейчас |

## Структура проекта

```
german-bot/
├── bot.py                 # Точка входа
├── config.py              # Конфигурация
├── database.py            # Работа с PostgreSQL
├── scheduler.py           # Расписание задач
├── handlers/
│   ├── commands.py        # Команды (/start, /stats, ...)
│   ├── messages.py        # Обработка текстовых сообщений
│   └── quiz.py            # Викторина и экзамен
├── services/
│   ├── gemini.py          # Gemini API
│   └── word_service.py    # Форматирование сообщений
├── .env.example
├── .gitignore
└── requirements.txt
```

## Деплой на сервер

1. Загрузи код на GitHub (`.env` не попадёт в git)
2. На сервере склонируй репозиторий
3. Создай `.env` с production-настройками
4. Установи зависимости и запусти через `systemd` или `screen`

```bash
# Пример запуска через screen
screen -S german-bot
python bot.py
# Ctrl+A, D — отсоединиться
```
