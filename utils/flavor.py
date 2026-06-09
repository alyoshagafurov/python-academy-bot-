"""The bot's personality — micro-moments of delight and mentor voice.

Pure helpers returning short, friendly, non-cringe lines. Used to make the
bot feel like a living mentor rather than a quiz machine.
"""
from __future__ import annotations

import random

_PRAISE = (
    "🎉 Верно!", "✅ Точно в цель!", "🔥 В яблочко!",
    "💪 Отлично!", "🚀 Так держать!", "😎 Красиво!",
)

_MOTIVATION = (
    "Ты начинаешь понимать Python 😎",
    "Сегодня ты сильнее, чем вчера 🔥",
    "Мозг прокачивается с каждым ответом 🧠",
    "Ещё чуть-чуть — и ты заговоришь на Python 🐍",
    "Вот это прогресс! Не останавливайся 💫",
    "Питон тобой доволен 🐍",
)

_WRONG = (
    "Почти! Подумай ещё разок 👀",
    "Мимо, но ты близко 🤏",
    "Не сдавайся — попробуй снова 💪",
    "Хмм, не то. Глянь на пример выше 🔎",
)

# Mentor lines for topics the user keeps stumbling on.
_MENTOR = {
    "print": "print() просто говорит вслух 🗣️ — что в кавычках, то и скажет.",
    "variables": "Переменные капризничают? 📦 Это коробка с наклейкой-именем.",
    "lists": "Хмм, list пока сопротивляется 😄 Представь рюкзак 🎒, счёт с нуля.",
    "loops": "Циклы любят порядок 🔁 Смотри, что именно повторяется.",
    "conditions": "Условие — это развилка 🚦 если / иначе.",
    "functions": "Функция — мини-завод 🛠️ принял аргумент → выдал результат.",
    "modules": "Модуль — готовый ящик с инструментами 🧰 сначала import, потом пользуйся.",
    "errors": "Ошибка — не конец света 🛡️ try ловит её, как страховочная сетка.",
    "oop": "Класс — чертёж 🍪 объект — печенька по нему. Не путай одно с другим.",
    "tools": "Это инструменты профи 🧰 не зубри — просто запомни, зачем каждый нужен.",
}


def praise() -> str:
    return random.choice(_PRAISE)


def motivation() -> str:
    return random.choice(_MOTIVATION)


def wrong_nudge() -> str:
    return random.choice(_WRONG)


def mentor_hint(topic: str) -> str:
    return _MENTOR.get(topic, "Давай разберём ещё проще 🙂")


def maybe_motivation(chance: float = 0.6) -> str:
    """Sometimes drop a motivational line (keeps it from feeling spammy)."""
    return motivation() if random.random() < chance else ""
