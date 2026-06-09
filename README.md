<div align="center">

# 🐍 Python Academy

### Telegram-бот, который учит программировать легко и с азартом

Теория через ассоциации, реальные примеры, мини-тесты и практика кода —
от первой строчки Python до постройки своего мира в **Minecraft**.

[![Python](https://img.shields.io/badge/Python-3.11+-3776AB?logo=python&logoColor=white)](https://www.python.org/)
[![aiogram](https://img.shields.io/badge/aiogram-3.x-2CA5E0?logo=telegram&logoColor=white)](https://docs.aiogram.dev/)
[![SQLite](https://img.shields.io/badge/SQLite-aiosqlite-003B57?logo=sqlite&logoColor=white)](https://www.sqlite.org/)
![Tests](https://img.shields.io/badge/tests-108%20passing-brightgreen)
![License](https://img.shields.io/badge/license-MIT-blue)

**▶️ Попробовать:** [@python_academy_tj_bot](https://t.me/python_academy_tj_bot)

</div>

---

## ✨ Что умеет бот

- 🎓 **Обучение через ассоциации** — каждая тема объясняется аналогией из жизни,
  реальным примером, разбором кода и частыми ошибками.
- 📚 **Несколько курсов** с раздельным прогрессом — Python, HTML & CSS, Python + Web
  и **Minecraft + Python**.
- 🧱 **Структура академии**: Курс → 📍 Этап → Урок, с разблокировкой по мере прохождения.
- 💻 **Готовые коды Minecraft** — библиотека скриптов: скопировал → вставил в VS Code → работает.
- 🧠 **Умное обучение** — анализ слабых тем, адаптивные подсказки, наставник-личность.
- 🎮 **Геймификация** — XP, уровни, 🔥 streak, 🏆 достижения, рейтинг и профиль.
- 🔍 **Поиск и избранное** по всей теории, похожие темы, «объясни проще».
- 💎 **PRO-режим** через feature-flags и оплату Telegram Stars.
- 🛠 **Админ-панель** — пользователи, retention, XP, контент.
- ⚙️ **Content Engine** — уроки и задачи в JSON: новые курсы добавляются **без кода**.

## 🧩 Курсы

| Курс | Содержание | Статус |
|------|-----------|--------|
| 🐍 **Python Beginner** | 7 этапов · 51 урок — синтаксис, типы, циклы, функции | ✅ Готов |
| 🟩 **Minecraft + Python** | 4 этапа · 43 урока — Python через управление миром игры | ✅ Готов |
| 🟣 **Python Student / Advanced** | 8 блоков — Production Python → … → Internals | 🚧 Блок 1 |
| 🎨 **HTML & CSS** | Структура, теги, стили, вёрстка | 🚧 В работе |
| 🌐 **Python + Web** | Flask, Jinja2, формы, деплой | 🚧 В работе |

> 🟩 **Minecraft + Python** — учишь Python, управляя реальным миром Minecraft через `mcpi`:
> ставишь блоки, строишь дома и замки, делаешь мини-игры. 4 этапа, 43 урока + библиотека
> из 20 готовых скриптов (постройки, эффекты, мини-игры, инструменты, пиксель-арт).

## 🛠 Технологии

`Python 3.11+` · `aiogram 3` · `aiosqlite` · `python-dotenv` · JSON Content Engine · SQLite (WAL)

## 🧱 Структура проекта

```
python-academy-bot/
├── bot.py                # точка входа (long-polling)
├── config.py             # настройки из .env
├── content/              # ⚙️ Content Engine — весь контент в JSON
│   ├── python/
│   │   ├── beginner/      # course.json + stage_*.json
│   │   └── minecraft/     # 🟩 курс Minecraft + Python
│   └── minecraft_snippets.json   # 💻 библиотека готовых кодов
├── handlers/             # обработчики (courses, lessons, snippets, admin…)
├── keyboards/            # inline-клавиатуры и callback-data
├── lessons/              # схема + загрузчик контента
├── services/             # бизнес-логика (прогресс, XP, рейтинг, оплата…)
├── states/               # FSM-состояния
├── utils/                # тексты, логирование, геймификация
└── tests/                # pytest (108 тестов)
```

## 🚀 Запуск

```bash
# 1. Виртуальное окружение
python3 -m venv .venv
source .venv/bin/activate

# 2. Зависимости
pip install -r requirements.txt

# 3. Токен бота — в .env (шаблон в .env.example)
echo "BOT_TOKEN=123456:ABC..." > .env

# 4. Старт
python bot.py
```

> Остановить: `Ctrl + C`.

## 🚂 Деплой на Railway

Бот работает на long-polling, поэтому ему нужен постоянный процесс и постоянный
диск для SQLite. На [Railway](https://railway.app) это пара минут:

1. **New Project → Deploy from GitHub repo** → выбери этот репозиторий.
   Сборка идёт через Nixpacks; команда запуска (`python bot.py`) уже задана в `railway.json`.
2. **Variables** → добавь:
   - `BOT_TOKEN` — токен от @BotFather
   - `DB_PATH` = `/data/academy.db`
   - `ADMIN_IDS` — твой Telegram ID (необязательно)
3. **Volumes** → New Volume, mount path `/data` (чтобы база переживала рестарты).
4. **Deploy.** В логах появится `🐍 Python Academy запущен как @...`.

> ⚠️ Один токен — один запущенный экземпляр. Останови локальный `python bot.py`,
> пока бот крутится на Railway (иначе Telegram вернёт `Conflict: getUpdates`).

## ⌨️ Команды

`/start` · `/menu` · `/courses` · `/codes` · `/search` · `/career` · `/projects` · `/invite` · `/profile`
Для админа: `/admin` · `/grant_pro <id>` · `/revoke_pro <id>`

## ➕ Как добавить курс или урок

Весь контент — в JSON, **код менять не нужно**:

- **Урок** → добавь объект в `content/<lang>/<track>/stage_N.json`
  (`title`, `theory`, `association`, `real_example`, `example`, `code_explained`,
  `common_mistakes`, `quiz` …).
- **Курс** → создай папку `content/<lang>/<track>/` с `course.json` + `stage_*.json`,
  загрузчик подхватит её сам. Поля описаны в `lessons/schema.py`.

## 🧪 Тесты

```bash
pytest -q          # 108 тестов: контент, прогресс, оплата, адаптивность…
```

## 📄 Лицензия

[MIT](LICENSE) © alyoshagafurov

<div align="center">
<sub>Сделано с ❤️ и щепоткой кубиков Minecraft 🟩</sub>
</div>
