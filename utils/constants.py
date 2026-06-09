"""Shared, content-agnostic constants (topic + difficulty vocabulary)."""
from __future__ import annotations

# Canonical topic keys used across lessons, practice, daily and stats.
TOPIC_NAMES: dict[str, str] = {
    # Stage 1 — Фундамент
    "install": "Установка и запуск",
    "variables": "Переменные",
    "types": "Типы данных",
    "io": "Ввод / вывод",
    "conditions": "Условия · if/else",
    "conversion": "Конвертация типов",
    # Stage 2 — Контейнеры и циклы
    "lists": "Списки · list",
    "tuple": "Кортежи · tuple",
    "slices": "Срезы",
    "while": "Цикл while",
    "loops": "Цикл for",
    "range": "range()",
    "strings": "Строки",
    "dict": "Словари · dict",
    "set": "Множества · set",
    "comprehension": "List comprehension",
    # Stage 3+ (used by placeholders / practice)
    "print": "Вывод · print()",
    "functions": "Функции",
    "modules": "Модули и файлы",
    "errors": "Ошибки и исключения",
    "oop": "ООП",
    "tools": "Инструменты разработчика",
    # ── Student track (advanced) ──
    "typing": "Type hints",
    "dataclass": "Dataclasses",
    "decorators": "Декораторы",
    "context_managers": "Контекстные менеджеры",
    "protocols": "Protocol / ABC",
    "di": "Dependency Injection",
    "solid": "SOLID",
    "async": "Async & Concurrency",
    "databases": "Базы данных",
    "web": "Web & API",
    "architecture": "Архитектура",
    "testing": "Тестирование и качество",
    "devops": "DevOps & Infra",
    "internals": "Внутренности Python",
    # ── Code Runner extra categories ──
    "algorithms": "Алгоритмы",
    "backend": "Backend-логика",
    # ── HTML & CSS track ──
    "html": "HTML — структура",
    "content": "Контент и медиа",
    "forms": "Формы",
    "css": "CSS — стили",
    "layout": "Вёрстка и сетки",
    # ── Python + Web track ──
    "templates": "Шаблоны Jinja2",
    "flask": "Flask",
    "forms_web": "Формы и данные",
    "deploy": "Статика и деплой",
}

# Short emoji per topic, used in cards and reminders.
TOPIC_EMOJI: dict[str, str] = {
    "install": "⚙️",
    "variables": "📦",
    "types": "🔢",
    "io": "🗣️",
    "conditions": "🚦",
    "conversion": "🔄",
    "lists": "🎒",
    "tuple": "📌",
    "slices": "✂️",
    "while": "🔁",
    "loops": "🔁",
    "range": "🔢",
    "strings": "🔤",
    "dict": "📒",
    "set": "🎲",
    "comprehension": "✨",
    "print": "🗣️",
    "functions": "🛠️",
    "modules": "📦",
    "errors": "🛡️",
    "oop": "🏗️",
    "tools": "🧰",
    # ── Student track (advanced) ──
    "typing": "🏷️",
    "dataclass": "🧱",
    "decorators": "🎁",
    "context_managers": "🚪",
    "protocols": "🔌",
    "di": "💉",
    "solid": "🏛️",
    "async": "⚡",
    "databases": "🗄️",
    "web": "🌐",
    "architecture": "🏛️",
    "testing": "🧪",
    "devops": "🐳",
    "internals": "🐍",
    # ── Code Runner extra categories ──
    "algorithms": "🧩",
    "backend": "🔧",
    # ── HTML & CSS track ──
    "html": "🧱",
    "content": "📄",
    "forms": "📝",
    "css": "🎨",
    "layout": "📐",
    # ── Python + Web track ──
    "templates": "🧩",
    "flask": "🍶",
    "forms_web": "📨",
    "deploy": "🚀",
}

DIFFICULTY_NAMES: dict[str, str] = {
    "easy": "🟢 Easy",
    "medium": "🟡 Medium",
    "hard": "🔴 Hard",
}

DIFFICULTY_XP: dict[str, int] = {
    "easy": 5,
    "medium": 10,
    "hard": 15,
}

# Categories available in Code Practice (topic key, label).
CODE_CATEGORIES: tuple[tuple[str, str], ...] = (
    ("variables", "📦 Variables"),
    ("lists", "🎒 Lists"),
    ("loops", "🔁 Loops"),
    ("functions", "🛠️ Functions"),
)


def topic_name(topic: str) -> str:
    return TOPIC_NAMES.get(topic, topic or "Тема")


def topic_emoji(topic: str) -> str:
    return TOPIC_EMOJI.get(topic, "📘")
