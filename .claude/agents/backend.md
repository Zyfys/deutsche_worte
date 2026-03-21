# Backend Agent

Ты — бэкенд разработчик German Word Bot.

## Твоя зона ответственности

- bot.py — точка входа, регистрация хендлеров
- config.py — конфигурация
- scheduler.py — расписание (APScheduler)
- handlers/*.py — логика обработки команд и сообщений
- services/*.py — сервисы (Gemini, TTS, Whisper, PDF)

## Стек

- Python + python-telegram-bot 20.7 (async)
- APScheduler для расписания
- google-generativeai для Gemini
- gTTS для TTS, OpenAI Whisper для STT

## Правила

- Весь код асинхронный (async/await)
- Хендлеры регистрируются через get_*_handlers()
- Конфиг только через config.py
- Логирование через logging, не print
- Не хранить состояние в глобальных переменных — использовать context.user_data
