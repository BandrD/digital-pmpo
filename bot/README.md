# Daily Bot — Telegram‑бот для ежедневных отчётов

Телеграм‑бот для автоматизации сбора ежедневных отчётов с поддержкой команд, голосовых сообщений, недельных планов и AI‑аналитики.

## 📋 Описание

Daily Bot автоматизирует процесс сбора ежедневных отчётов в командах разработки. Бот:

- **Автоматически приглашает** на дейли в заданное время
- **Собирает ответы** на вопросы (текст и голос)
- **Транскрибирует голосовые** сообщения (Vosk)
- **Формирует отчёт по статусу команды** (опционально, Mistral)
- **Отправляет сводку** менеджеру и/или в групповой чат команды
- **Управляет командами** (создание, настройки, участники)
- **Отслеживает отпуска** сотрудников
- **Планы на неделю**: сбор и напоминания по weekly‑планам
- **Адаптивная доска задач**: общая ссылка или персональная GitVerse‑ссылка
- **Уточняющий вопрос (опционально)** от ИИ после основных вопросов

## ⚡ Основные возможности

### Для сотрудников
- Регистрация через инвайт/команду
- Автополучение вопросов в установленное время
- Ответы текстом или голосом
- Личные настройки в разрезе команды: роль, время дейли, GitVerse‑ник, отпуск

### Для менеджеров
- Управление командами (создание — только для кураторов)
- Просмотр и отправка отчётов
- Настройка времени опросов и дней недели
- Управление участниками и вопросами команды

## 🐳 Быстрый старт в Docker

Требуется установленный Docker и Docker Compose.

1) Создайте `.env` в корне проекта (см. «Конфигурация» ниже).

2) Запустите контейнеры:

```bash
docker compose up -d --build
```

Это поднимет:
- сервис `db` (PostgreSQL 14, данные сохраняются в volume `postgres_data`)
- сервис `bot` (Python 3.10, код примонтирован как volume `./bot:/app/bot`)

Логи бота:

```bash
docker compose logs -f bot
```

Остановка:

```bash
docker compose down
```

Альтернатива с Makefile:

```bash
make up      # запустить
make build   # собрать и запустить
make down    # остановить и удалить
```

Примечания:
- Бот при старте сам выполняет инициализацию/миграции БД.
- Порт БД пробрасывается из переменной `PGPORT` (по умолчанию 55432).

## 🛠️ Локальная установка (без Docker)

1) Клонируйте репозиторий:

```bash
git clone <URL_репозитория>
cd Dailybot
```

2) Создайте и активируйте виртуальное окружение:

```bash
# Windows
python -m venv venv
venv\Scripts\activate

# Linux/macOS
python3 -m venv venv
source venv/bin/activate
```

3) Установите зависимости:

```bash
pip install -r requirements.txt
```

4) Создайте `.env` (см. ниже) и запустите бота из корня проекта:

```bash
python -m bot.main
```

Важно: запуск из каталога `bot` командой `python main.py` некорректен из‑за абсолютных импортов (`from bot...`). Используйте модульный запуск из корня проекта: `python -m bot.main`.

## ⚙️ Конфигурация (.env)

Создайте в корне проекта файл `.env`:

```env
# Бот MAX. Токен: business.max.ru → Чат-боты → Настройки.
MAX_BOT_TOKEN=ваш_токен_бота_MAX
TIMEZONE=Asia/Yekaterinburg

# (опционально) Список админов, JSON-массив id пользователей MAX
ADMINS_MAX_IDS=[123456789, 987654321]

# PostgreSQL: используйте либо единый DSN, либо поля ниже
# DATABASE_URL=postgresql://user:password@host:port/dbname?sslmode=disable
PGHOST=127.0.0.1
PGPORT=55432
PGDATABASE=dailybot
PGUSER=dailybot
PGPASSWORD=ваш_пароль
PGSSLMODE=disable

# Пул соединений PostgreSQL
PGPOOL_MIN=1
PGPOOL_MAX=10

# LLM (опционально, OpenRouter). Без ключей дейли собирается, сводка от модели не строится.
OPENROUTER_FREE_KEY=
OPENROUTER_PAID_KEY=
```

Как получить MAX_BOT_TOKEN: business.max.ru → Чат-боты → бот → Настройки.

## 📁 Структура проекта (актуальная)

```
Dailybot/
├── bot/
│   ├── core/
│   │   ├── bot_instance.py
│   │   ├── database.py
│   │   └── states.py
│   ├── handlers/
│   │   ├── admin_handlers.py
│   │   ├── cancel_handlers.py
│   │   ├── daily_handlers.py
│   │   ├── employee_handlers.py
│   │   ├── group_handlers.py
│   │   ├── main_handlers.py
│   │   ├── manager_handlers.py
│   │   ├── registration_handlers.py
│   │   ├── team_edit_handlers.py
│   │   ├── team_handlers.py
│   │   ├── team_questions_handlers.py
│   │   └── weekly_plan_handlers.py
│   ├── utils/
│   │   ├── filters.py
│   │   ├── keyboards.py
│   │   ├── llm_utils.py
│   │   ├── scheduler_jobs.py
│   │   ├── scheduler_manager.py
│   │   ├── text_constants.py
│   │   ├── utils.py
│   │   └── voice_utils.py
│   ├── CHANGES/
│   │   ├── CANCEL_LOGIC_README.md
│   │   ├── TEAM_TIME_SETTINGS_README.md
│   │   ├── SCHEDULER_SUMMARY.md
│   │   ├── REPORT_LOGIC_FIX.md
│   │   ├── REFACTORING_SUMMARY.md
│   │   └── INTERACTIVE_DAYS_SUMMARY.md
│   ├── config.py
│   └── main.py
├── docker-compose.yml
├── bot/Dockerfile
├── db/Dockerfile
├── requirements.txt
└── Makefile
```

## 🗃 База данных и миграции

- Минимальная версия PostgreSQL: 13+ (рекомендовано 14/15)
- При старте бот выполняет инициализацию БД и «ленивые» миграции:
  - создание таблиц, если их нет
  - добавление недостающих колонок/индексов (например, метрики `duration_ms`, `attempts` в `llm_token_usage`, `is_participant` в `user_team_memberships`, уникальный индекс weekly‑планов)

Ключевые таблицы (как в текущем коде инициализации):

- `teams`: id, name, chat_id, chat_topic_id, board_link, morning_time, evening_time, report_time, report_days, timezone, created_at, test_flag, questions_json (jsonb '[]')
- `employees`: tg_id, username, full_name, team_id (текущая выбранная команда)
- `user_team_memberships`: employee_tg_id, team_id, is_manager, role, daily_time (default 'morning'), gitverse_nickname, vacation_start, vacation_end, is_participant
- `reports`: employee_tg_id, team_id, report_datetime, llm_questions, llm_answer, answers_json (jsonb, default '[]')
- `team_invites`: одна активная ссылка‑приглашение на команду (UNIQUE по team_id)
- `llm_token_usage`: event, team_id, employee_tg_id, provider, model, model_version, input_tokens, output_tokens, total_tokens, duration_ms, attempts, created_at
- `weekly_plans`: планы на неделю с уникальностью (employee_tg_id, team_id, week_start_date)
- `curators`: tg_id пользователей, имеющих право создавать команды

Пример добавления куратора вручную:

```sql
INSERT INTO curators (tg_id) VALUES (123456789) ON CONFLICT DO NOTHING;
```

## ⏰ Расписание, дни и часовые пояса

- Для каждой команды настраиваются: `morning_time`, `evening_time`, `report_time`, `report_days` и `timezone`.
- Дни утренних/вечерних опросов выводятся логикой бота из настроек и фиксированных групп `morning`/`evening`.
- Все расписания создаются с учётом часового пояса команды
- В приглашениях явно указывается дедлайн с поясом: «сегодня/завтра, HH:MM (МСК/ЕКБ)».

## 🎤 Голосовые сообщения

- Поддержка OGG/WAV
- Движок: Vosk (`vosk-model-small-ru-0.22`)
- Асинхронная транскрипция

## 🤖 LLM (опционально)

- При наличии `MISTRAL_API_KEY` бот может:
  - сформировать «Отчёт по статусу команды»
  - задать один уточняющий вопрос после основных
- Учёт токенов пишется в `llm_token_usage` с метриками и привязкой к команде/пользователю (если известны).

## 🔍 Команды бота

- `/start` — регистрация и главное меню
- `/create_command` — создать команду (для кураторов)
- `/show_id` — показать ID чата/топика (в группе)

Также доступны действия в меню бота для сотрудников и менеджеров: изменение личных данных, настройка времени дейли, управление отпусками, настройка команды и вопросов, просмотр отчётов.

## 📝 Логирование

- Уровень: INFO
- Часовой пояс: из настроек
- Логи включают операции с БД, отправку сообщений, ошибки

# 🔧 Дополнительные возможности

### Мультикоманды:
- Поддержка нескольких команд в одном боте
- Изолированные отчеты для каждой команды
- Настройка отдельных чатов и топиков

### Валидация данных:
- Проверка формата имен (Имя И.)
- Ограничения на длину полей
- Валидация ID чатов и топиков

## 🔗 Адаптивная доска задач (GitVerse и обычные)

- Менеджер может указать ссылку на доску: `Настройки → Доска`.
- Поддерживаются любые URL. Если это GitVerse tasktracker (например: `https://gitverse.ru/org/repo/tasktracker?view=board`), бот:
  - При регистрации попросит у сотрудников ник GitVerse.
  - В вопросе дейли будет показывать персональную ссылку «Доска (ваши задачи)» с фильтром по сотруднику.
- Если указан другой трекер или ник отсутствует, в вопросе показывается «Доска команды» со ссылкой, указанной менеджером.
- Ссылка должна начинаться с `http://` или `https://`. Подсказки по вводу отображаются при редактировании ссылки в интерфейсе бота.