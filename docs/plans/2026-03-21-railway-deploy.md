# Railway Deploy Implementation Plan

**Goal:** Опубликовать бота на Railway с автодеплоем из GitHub (git push → Railway пересобирает и перезапускает).

**Architecture:** Код живёт на GitHub → Railway слушает ветку `main` → при каждом пуше пересобирает Docker-образ и перезапускает бота. PostgreSQL — Railway Postgres (managed), переменные окружения — Railway Environment Variables (не .env файл).

**Tech Stack:** Railway, GitHub, Docker (Dockerfile), PostgreSQL on Railway

---

## Chunk 1: Подготовка репозитория

### Task 1: Git-репозиторий и .gitignore

**Files:**
- Create: `german-bot/.gitignore`
- (корень проекта `worte deutch/`)

- [ ] **Step 1: Создать .gitignore**

Файл `german-bot/.gitignore`:
```
.env
__pycache__/
*.pyc
*.pyo
bot.log
*.log
.DS_Store
```

- [ ] **Step 2: Инициализировать git в папке german-bot**

```bash
cd "c:\Users\zyfys\projects\worte deutch\german-bot"
git init
git add .
git status   # убедись что .env НЕ в списке
git commit -m "feat: initial bot commit"
```

- [ ] **Step 3: Создать репозиторий на GitHub**

1. Открой https://github.com/new
2. Название: `german-word-bot` (private или public — на выбор)
3. НЕ добавляй README, .gitignore, license (у нас уже есть)
4. Нажми Create

- [ ] **Step 4: Привязать remote и запушить**

```bash
git remote add origin https://github.com/ВАШ_ЛОГИН/german-word-bot.git
git branch -M main
git push -u origin main
```

---

## Chunk 2: Dockerfile

### Task 2: Создать Dockerfile

**Files:**
- Create: `german-bot/Dockerfile`

Railway умеет деплоить Python без Docker, но Dockerfile даёт полный контроль над окружением.

- [ ] **Step 1: Создать Dockerfile**

```dockerfile
FROM python:3.12-slim

WORKDIR /app

# Системные зависимости для pydub/gTTS/pdfplumber
RUN apt-get update && apt-get install -y \
    ffmpeg \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

CMD ["python", "bot.py"]
```

- [ ] **Step 2: Закоммитить**

```bash
git add Dockerfile
git commit -m "feat: add Dockerfile for Railway deploy"
git push
```

---

## Chunk 3: Деплой на Railway

### Task 3: Настроить Railway проект

- [ ] **Step 1: Создать аккаунт и проект на Railway**

1. Открой https://railway.app
2. Sign in with GitHub
3. New Project → Deploy from GitHub repo
4. Выбери `german-word-bot`
5. Railway обнаружит Dockerfile и начнёт первый билд

- [ ] **Step 2: Добавить PostgreSQL**

В том же проекте Railway:
1. New → Database → Add PostgreSQL
2. Railway создаст базу и переменную `DATABASE_URL` автоматически
3. Перейди в Settings базы → Variables → скопируй `DATABASE_URL`

- [ ] **Step 3: Добавить переменные окружения**

В Railway → твой сервис (бот) → Variables → добавь:

| Переменная | Значение |
|---|---|
| `TELEGRAM_BOT_TOKEN` | твой токен |
| `GROQ_API_KEY` | твой ключ |
| `GROQ_MODEL` | `llama-3.3-70b-versatile` |
| `DATABASE_URL` | автоматически прокинут из Postgres сервиса |
| `OPENAI_API_KEY` | если используешь Whisper, иначе можно пропустить |

> **Важно:** `DATABASE_URL` от Railway имеет формат `postgresql://...` — psycopg2 его принимает напрямую.

- [ ] **Step 4: Проверить первый деплой**

1. Railway → Deployments → смотри логи
2. Должно появиться: `Bot is running...` и `Application started`
3. Если ошибка — читай логи, скорее всего не задана переменная

- [ ] **Step 5: Проверить бота в Telegram**

Отправь `/start` боту — должен ответить.

---

## Chunk 4: Автодеплой

### Task 4: Проверить автодеплой

- [ ] **Step 1: Сделать любое изменение и запушить**

```bash
# Например, добавь строку в README.md
echo "# Deployed on Railway" >> README.md
git add README.md
git commit -m "test: verify auto-deploy"
git push
```

- [ ] **Step 2: Убедиться что Railway подхватил пуш**

Railway → Deployments — должен появиться новый деплой автоматически.

- [ ] **Step 3: Удалить .env с локальной машины из git (если случайно попал)**

```bash
git ls-files | grep .env   # если что-то есть — удалить из git
```

---

## Итог

После выполнения:
- Код на GitHub (`main` ветка)
- Бот работает на Railway 24/7
- PostgreSQL на Railway (managed, бэкапы включены)
- `git push` → автоматический редеплой за ~1-2 минуты
- Локальный `.env` остаётся для разработки, в продакшне — Railway Variables

## Стоимость Railway

- **Hobby план: $5/мес** — включает $5 кредитов на ресурсы
- Telegram-бот + Postgres обычно укладываются в эти $5
- Первые 500 часов в месяц бесплатно на Trial (требует верификации карты)
