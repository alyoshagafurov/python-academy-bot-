"""Practice Mode content: questions by category (topic) and difficulty."""
from __future__ import annotations

from lessons.schema import Quiz

# Practice categories shown in the menu (topic key, label).
CATEGORIES: tuple[tuple[str, str], ...] = (
    ("variables", "📦 Variables"),
    ("loops", "🔁 Loops"),
    ("conditions", "🚦 If / Else"),
    ("lists", "🎒 Lists"),
    ("functions", "🛠️ Functions"),
)

DIFFICULTIES: tuple[str, ...] = ("easy", "medium", "hard")


def _q(question: str, code: str, options: tuple[str, ...], correct: int,
       explanation: str, topic: str) -> Quiz:
    return Quiz(question=question, code=code, options=options,
               correct=correct, explanation=explanation, topic=topic)


# (topic, difficulty) -> pool of questions
PRACTICE: dict[tuple[str, str], tuple[Quiz, ...]] = {
    # ── Variables ──────────────────────────────────────────────────────────
    ("variables", "easy"): (
        _q("Что выведет код?", "a = 3\nb = 4\nprint(a + b)",
           ("7", "34", "ab", "Ошибка"), 0, "3 + 4 = 7.", "variables"),
    ),
    ("variables", "medium"): (
        _q("Что выведет код?", "x = 2\nx = x * 3\nprint(x)",
           ("6", "23", "2", "Ошибка"), 0, "x = 2, затем 2 * 3 = 6.", "variables"),
    ),
    ("variables", "hard"): (
        _q("Что выведет код?", "a, b = 1, 2\na, b = b, a\nprint(a, b)",
           ("1 2", "2 1", "2 2", "Ошибка"), 1,
           "Обмен значениями: a и b меняются местами → 2 1.", "variables"),
    ),
    # ── Loops ──────────────────────────────────────────────────────────────
    ("loops", "easy"): (
        _q("Сколько раз напечатается «Привет»?", "for i in range(3):\n    print('Привет')",
           ("3", "2", "4", "0"), 0, "range(3) → 0, 1, 2 — три повтора.", "loops"),
    ),
    ("loops", "medium"): (
        _q("Что выведет код?", "for i in range(3):\n    print(i)",
           ("1 2 3", "0 1 2", "0 1 2 3", "3"), 1, "range(3) даёт 0, 1, 2.", "loops"),
    ),
    ("loops", "hard"): (
        _q("Чему будет равна сумма?", "s = 0\nfor i in range(1, 4):\n    s = s + i\nprint(s)",
           ("6", "3", "10", "4"), 0, "range(1, 4) = 1, 2, 3; 1 + 2 + 3 = 6.", "loops"),
    ),
    # ── If / Else ──────────────────────────────────────────────────────────
    ("conditions", "easy"): (
        _q("Что выведет код?", "x = 5\nif x > 3:\n    print('много')\nelse:\n    print('мало')",
           ("много", "мало", "5", "Ошибка"), 0, "5 > 3 — истина → «много».", "conditions"),
    ),
    ("conditions", "medium"): (
        _q("Что выведет код?",
           "x = 2\nif x > 5:\n    print('A')\nelif x > 1:\n    print('B')\nelse:\n    print('C')",
           ("A", "B", "C", "AB"), 1, "x > 5 ложь, x > 1 истина → B.", "conditions"),
    ),
    ("conditions", "hard"): (
        _q("Что выведет код?",
           "age = 18\nif age >= 18 and age < 65:\n    print('взрослый')\nelse:\n    print('другой')",
           ("взрослый", "другой", "18", "Ошибка"), 0,
           "18 >= 18 и 18 < 65 — оба истинны → взрослый.", "conditions"),
    ),
    # ── Lists ──────────────────────────────────────────────────────────────
    ("lists", "easy"): (
        _q("Сколько элементов в списке?", "nums = [5, 10, 15]\nprint(len(nums))",
           ("3", "2", "15", "Ошибка"), 0, "len считает элементы: их 3.", "lists"),
    ),
    ("lists", "medium"): (
        _q("Что выведет код?", "a = [1, 2, 3]\na.append(4)\nprint(a[-1])",
           ("4", "3", "1", "Ошибка"), 0,
           "append добавил 4 в конец; a[-1] — последний → 4.", "lists"),
    ),
    ("lists", "hard"): (
        _q("Что выведет код?", "a = [1, 2, 3, 4]\nprint(a[1:3])",
           ("[2, 3]", "[1, 2, 3]", "[2, 3, 4]", "[1, 2]"), 0,
           "Срез [1:3] берёт индексы 1 и 2 → [2, 3].", "lists"),
    ),
    # ── Functions ──────────────────────────────────────────────────────────
    ("functions", "easy"): (
        _q("Что выведет код?", "def hi():\n    print('Привет')\nhi()",
           ("Привет", "hi", "ничего", "Ошибка"), 0,
           "Вызов hi() запускает функцию → Привет.", "functions"),
    ),
    ("functions", "medium"): (
        _q("Что выведет код?", "def double(x):\n    return x * 2\nprint(double(5))",
           ("10", "5", "55", "Ошибка"), 0, "double(5) возвращает 5 * 2 = 10.", "functions"),
    ),
    ("functions", "hard"): (
        _q("Что выведет код?", "def add(a, b=10):\n    return a + b\nprint(add(5))",
           ("15", "5", "510", "Ошибка"), 0,
           "b по умолчанию 10; 5 + 10 = 15.", "functions"),
    ),
}


def get_question(topic: str, difficulty: str, index: int) -> Quiz | None:
    pool = PRACTICE.get((topic, difficulty))
    if not pool:
        return None
    return pool[index % len(pool)]


def pool_size(topic: str, difficulty: str) -> int:
    return len(PRACTICE.get((topic, difficulty), ()))
