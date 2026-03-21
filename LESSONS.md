# Уроки и заметки

## 💡 Что узнал

- Python в системе не найден как `python`, нужен полный путь: `C:\Users\zyfys\AppData\Local\Python\bin\python.exe`
- psql не в PATH — подключение к БД проверять через Python скрипт, не через CLI
- Репозитории скилов изменились: `anthropics/claude-code` → `anthropics/skills`, `obra/systematic-debugging` → `obra/superpowers`
- `sanjay3290/` и `composiohq/` репозитории недоступны публично — не использовать
- **Правило:** перед установкой скила всегда делать `--list` — экосистема меняется быстро

## ⚠️ Что не делать

- Не запускать бота через `python bot.py` без полного пути к интерпретатору на этой машине
- Не коммитить .env файл — в .gitignore уже настроен
- Не отвязывать биллинг от существующего Cloud проекта — проект теряет free tier (limit: 0). Вместо этого создавать новый проект через AI Studio

## 🔧 Полезные команды

```bash
# Запуск бота (полный путь к Python)
cd "c:\Users\zyfys\projects\worte deutch\german-bot"
"C:\Users\zyfys\AppData\Local\Python\bin\python.exe" bot.py

# Установка зависимостей
"C:\Users\zyfys\AppData\Local\Python\bin\python.exe" -m pip install -r requirements.txt

# Проверка подключения к БД
"C:\Users\zyfys\AppData\Local\Python\bin\python.exe" -c "from database import init_db; init_db(); print('DB OK')"
```
