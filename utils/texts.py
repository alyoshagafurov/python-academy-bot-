"""All user-facing message templates (HTML formatted).

Copy lives here so the bot's tone is easy to tune and handlers stay focused
on flow. Functions are pure: they take data and return strings.
"""
from __future__ import annotations

import html
import re

from lessons import Lesson, Stage, get_course, get_stage, total_lessons
from lessons.schema import CodeTask, Quiz
from services import course_service, feature_service, pricing, sandbox
from services.achievement_service import Achievement
from services.code_service import CodeResult
from services.daily_service import DailyResult
from services.leaderboard_service import Leaderboard
from services.lesson_service import CHALLENGE_XP, CompleteResult
from services.level_service import LevelInfo
from services.practice_service import PracticeAnswer
from services.reward_service import ActivityResult
from services.stats_service import KnowledgeSummary
from utils import flavor
from utils.constants import DIFFICULTY_NAMES, topic_emoji, topic_name
from utils.gamification import progress_bar


_TAG_RE = re.compile(r"<[^>]+>")


def _code_block(code: str) -> str:
    return f'<pre><code class="language-python">{html.escape(code)}</code></pre>'


def _join(*parts: str) -> str:
    """Join non-empty sections with blank lines between them."""
    return "\n\n".join(part for part in parts if part)


def _activity_feedback(activity: ActivityResult | None) -> str:
    """Lines announcing level-ups, new achievements and streak growth."""
    if activity is None:
        return ""
    lines: list[str] = []
    if activity.leveled_up:
        lines.append(f"🎉 <b>Новый уровень!</b> {activity.level.title} · Level {activity.level.level}")
    for ach in activity.new_achievements:
        lines.append(f"🏅 Достижение: {ach.emoji} <b>{ach.title}</b>")
    if activity.streak.increased and activity.streak.streak > 1:
        lines.append(f"🔥 Streak: {activity.streak.streak} дней подряд!")
    return "\n".join(lines)


def smart_motivation(user, level: LevelInfo, done: int, total: int) -> str:
    if level.to_next <= 40:
        return f"🔥 До <b>Level {level.level + 1}</b> осталось всего {level.to_next} XP!"
    if done >= total:
        return "🏆 Весь курс пройден — ты настоящий питонист! 🐍 Загляни в 🧪 Практику и 💻 Code."
    if done == 0:
        return "🚀 С чего начать? Жми <b>«Начать обучение»</b> — это пара минут!"
    if user.streak >= 3:
        return f"🔥 {user.streak} дней подряд — так держать!"
    return f"💪 Пройдено {done} из {total} уроков. Продолжаем!"


# ─────────────────────────── Onboarding & menus ───────────────────────────

def onboarding(first_name: str | None) -> str:
    name = html.escape(first_name or "друг")
    return (
        f"👋 <b>Привет, {name}!</b>\n\n"
        "Это <b>Python Knowledge Hub</b> 🐍 — понятная теория Python и backend в одном месте.\n\n"
        "Что здесь есть:\n"
        "📚 структурированные курсы с объяснениями\n"
        "🔗 ассоциации и примеры из жизни\n"
        "🔍 быстрый поиск по любой теме\n"
        "💡 режим «объяснить проще»\n"
        "⭐ избранное и 🧠 умные рекомендации\n\n"
        "Читай в своём темпе — без тестов и спешки 📖\n\n"
        "Выбирай, с чего начать 👇"
    )


def hub(user, level: LevelInfo = None, suggestion=None,
        tracks: list[tuple[str, int]] | None = None) -> str:
    tracks_line = "  ·  ".join(f"{label} {pct}%" for label, pct in tracks) if tracks else ""
    streak_line = f"🔥 {user.streak} дн. подряд" if user.streak else ""
    return _join(
        "🐍 <b>Python Knowledge Hub</b>",
        "Теория, понятные объяснения и быстрый поиск. Учись в своём темпе 📖",
        tracks_line,
        streak_line,
        "Что почитаем сегодня? 👇",
    )


def about() -> str:
    return (
        "ℹ️ <b>О боте</b>\n\n"
        "<b>Python Knowledge Hub</b> — справочник и учебник по Python 🐍\n\n"
        "Что внутри:\n"
        "📚 два курса: Beginner и Student (backend)\n"
        "📖 теория с ассоциациями, примерами и разбором\n"
        "🔍 быстрый поиск по всем темам\n"
        "💡 «объяснить проще» для сложных мест\n"
        "🔗 похожие темы рядом с каждой\n"
        "⭐ избранное и 🧠 персональные рекомендации\n\n"
        "Никаких тестов и гонки — только понятная теория, когда она нужна 💪"
    )


def choose_mode(need_choice: bool = False) -> str:
    intro = "Сначала выбери уровень обучения 👇" if need_choice else "С чего начнём путешествие в Python?"
    return (
        "🎯 <b>Выбери свой уровень</b>\n\n"
        f"{intro}\n\n"
        "🟢 <b>Детский</b> — для самых маленьких\n"
        "🔵 <b>Новичок</b> — основы с нуля <i>(доступно)</i>\n"
        "🟣 <b>Студент</b> — глубокое погружение\n\n"
        "Сейчас открыт режим <b>🔵 Новичок</b> 👇"
    )


def coming_soon() -> str:
    return (
        "🚧 <b>Скоро появится!</b>\n\n"
        "Этот режим ещё в разработке 🛠️\n"
        "Мы готовим для него крутые уроки 💜\n\n"
        "А пока прокачайся в режиме <b>🔵 Новичок</b> — "
        "там тебя ждут уроки, практика и код! 👇"
    )


# ───────────────────────── Learning Path & lessons ────────────────────────

def course_selection(infos) -> str:
    """Course picker — `infos` is a list of (course, percent)."""
    blocks = []
    for course, pct in infos:
        line = f"{course.emoji} <b>{course.title}</b> · {pct}%"
        if course.description:
            line += f"\n{course.description}"
        blocks.append(line)
    return _join("📚 <b>Выбери курс</b>", *blocks, "Выбери трек 👇")


def course_overview(course: "Course", current_lesson: int, xp_earned: int) -> str:
    """Course screen: stage list with per-stage progress (Codecademy-style)."""
    done, total, percent = course_service.course_progress(current_lesson, course)

    rows = []
    for sp in course_service.all_stage_progress(current_lesson, course):
        stage = sp.stage
        if sp.status == "locked":
            rows.append(f"🔒 <b>Этап {stage.id}.</b> {stage.title}")
        else:
            rows.append(f"{sp.icon} <b>Этап {stage.id}.</b> {stage.title} — {sp.percent}%")
    tree = "\n".join(rows)

    if done >= total:
        tail = "🎉 Весь курс пройден — легенда! 🐍"
    elif done == 0:
        tail = "👇 Начни с <b>Этапа 1</b> — жми на него или «▶️ Продолжить»."
    else:
        tail = "Этапы открываются по порядку — заверши текущий, чтобы открыть следующий 🔓"
    return _join(
        f"{course.emoji} <b>{course.title}</b>",
        f"{progress_bar(done, total)} {percent}%   ·   ⚡ {xp_earned} XP   ·   {done}/{total} уроков",
        tree,
        tail,
    )


def backend_journey(course: "Course", current_lesson: int) -> str:
    """Student-track progression screen — blocks + identity (dopamine-friendly)."""
    done, total, percent = course_service.course_progress(current_lesson, course)
    rows = []
    for sp in course_service.all_stage_progress(current_lesson, course):
        icon = {"done": "✅", "current": "🔓", "locked": "🔒"}[sp.status]
        badge = ""
        if sp.status == "done":
            ident = course_service.identity_for_stage(sp.stage.id)
            badge = f" — <i>{ident[1]}</i>" if ident else ""
        rows.append(f"{sp.stage.emoji} {sp.stage.title} {icon}{badge}")

    ident = course_service.current_identity(current_lesson, course)
    title_line = (
        f"🎖 Твой титул: <b>{ident[0]} {ident[1]}</b>"
        if ident else "🎖 Титул: <i>пройди Блок 1, чтобы получить первый</i>"
    )
    return _join(
        "🧭 <b>Backend Journey</b>",
        f"{progress_bar(done, total)} {percent}%   ·   🎯 Junior Python Backend",
        "\n".join(rows),
        title_line,
        "Жми на открытый блок и качай скилл 👇" if done < total else "🐍 Ты прошёл весь путь — Middle ждёт!",
    )


def stage_overview(stage: Stage, current_lesson: int) -> str:
    """Stage screen: lesson tree with progress (Duolingo-style path)."""
    sp = course_service.stage_progress(stage, current_lesson)
    rows = []
    for index, lesson in enumerate(stage.lessons, start=1):
        icon = course_service.lesson_icon(lesson.id, current_lesson)
        tag = " 🚧" if lesson.placeholder else ""
        rows.append(f"{icon} {index}. {lesson.title}{tag}")
    tree = "\n".join(rows)
    return _join(
        f"{stage.emoji} <b>Этап {stage.id}: {stage.title}</b>\n<i>{stage.subtitle}</i>",
        f"{progress_bar(sp.done, sp.total)} {sp.percent}%   ·   ⚡ {sp.xp_earned} XP   ·   {sp.done}/{sp.total}",
        tree,
        "✅ пройден    ▶️ доступен    🔒 закрыт",
    )


def placeholder_lesson(lesson: Lesson, course: "Course | None" = None) -> str:
    stage = (course or get_course()).stage(lesson.stage_id)
    location = f"{stage.emoji} Этап {stage.id}: {stage.title}" if stage else ""
    return _join(
        f"🚧 <b>{lesson.title}</b>",
        location,
        "Этот урок уже в разработке — мы пишем его прямо сейчас 🛠️\n"
        "Скоро здесь появится полноценная глава: объяснение, ассоциация, "
        "разбор кода, практика, тест и challenge.",
        "А пока заверши доступные уроки — ты отлично идёшь! 💪",
    )


def lesson_card(lesson: Lesson, adaptive: str = "", course: "Course | None" = None,
                advanced: bool = False) -> str:
    """Theory card — pure reading: explanation, analogy, example, common mistakes."""
    course = course or get_course()
    stage = course.stage(lesson.stage_id)
    number = course_service.lesson_number_in_stage(lesson, course)
    location = f"{stage.emoji} {course.title} · Этап {stage.id} · Тема {number}/{stage.total}" if stage else ""
    mistakes = "\n".join(f"• {m}" for m in lesson.common_mistakes)
    return _join(
        f"📖 <b>{lesson.title}</b>",
        location,
        adaptive,
        lesson.theory,
        f"🔗 <b>Ассоциация</b>\n{lesson.association}",
        f"🌍 <b>Где встречается</b>\n{lesson.real_example}",
        f"💻 <b>Пример</b>\n{_code_block(lesson.example)}",
        f"🔍 <b>Разбор</b>\n{lesson.code_explained}",
        f"⚠️ <b>Частые ошибки</b>\n{mistakes}" if mistakes else "",
    )


def _plain(text: str) -> str:
    """Strip HTML tags for a short plain-text essence."""
    return _TAG_RE.sub(" ", text or "").strip()


def _first_sentence(text: str) -> str:
    plain = _plain(text)
    for sep in (". ", "! ", "? "):
        if sep in plain:
            return plain.split(sep)[0].strip() + "."
    return plain[:200]


def lesson_simple(lesson: Lesson) -> str:
    """'Explain simpler' — analogy-first, stripped to the essence."""
    parts = [
        f"💡 <b>Проще про «{lesson.title}»</b>",
        f"🔗 {lesson.association}" if lesson.association else "",
        f"В двух словах: {_first_sentence(lesson.theory)}" if lesson.theory else "",
    ]
    if lesson.example:
        parts.append(f"Пример:\n{_code_block(lesson.example)}")
    if lesson.common_mistakes:
        parts.append(f"⚠️ Не споткнись: {_plain(lesson.common_mistakes[0])}")
    parts.append("Нужно подробнее — жми 📖 <b>Полная версия</b> 👇")
    return _join(*parts)


_SNIPPET_DIFF = {"easy": "🟢 Легко", "medium": "🟡 Средне", "hard": "🔴 Сложно"}


def snippets_intro(categories) -> str:
    """Code-library home — `categories` is a list of (emoji, title, count)."""
    rows = [f"{emoji} <b>{title}</b> · {count}" for emoji, title, count in categories]
    return _join(
        "💻 <b>Готовые коды для Minecraft</b>",
        "Скопируй → вставь в VS Code → запусти. Каждый скрипт сразу работает в Minecraft 🟩",
        "\n".join(rows),
        "Выбери категорию 👇",
    )


def snippet_list(emoji: str, title: str, snips) -> str:
    """One category — `snips` is a list of Snippet objects."""
    rows = [f"{_SNIPPET_DIFF.get(s.difficulty, '🟢')[:2]} {s.title} — {s.description}"
            for s in snips]
    return _join(f"{emoji} <b>{title}</b>", "\n".join(rows), "Выбери скрипт 👇")


def snippet_card(snip) -> str:
    """A single ready-to-copy script."""
    diff = _SNIPPET_DIFF.get(snip.difficulty, "🟢 Легко")
    parts = [
        f"💻 <b>{snip.title}</b>",
        f"{snip.description}\n{diff}",
        "📋 <b>Скопируй и запусти в VS Code:</b>",
        _code_block(snip.code),
    ]
    if snip.tip:
        parts.append(f"💡 <i>{snip.tip}</i>")
    return _join(*parts)


def related_list(source: Lesson, items) -> str:
    if not items:
        return _join(
            f"🔗 <b>Похожие темы · {source.title}</b>",
            "Пока без прямых связей — загляни в 🔍 Поиск или 📚 Курсы.",
        )
    lines = [f"{topic_emoji(r.lesson.topic)} {r.lesson.title}" for r in items]
    return _join(
        f"🔗 <b>Похожие темы</b>",
        f"Связано с «<b>{source.title}</b>»:",
        "\n".join(lines),
        "Открой любую тему 👇",
    )


# ─────────────────────── Search · Favorites · Recommend ───────────────────

def search_prompt() -> str:
    return _join(
        "🔍 <b>Поиск по теории</b>",
        "Напиши слово или тему — найду нужные объяснения по всем курсам.",
        "Например: <i>словари</i>, <i>цикл</i>, <i>декораторы</i>, <i>async</i>, <i>SOLID</i>.",
    )


def search_results(query: str, hits) -> str:
    safe = html.escape(query)
    if not hits:
        return _join(
            f"🔍 <b>Поиск: «{safe}»</b>",
            "Ничего не нашёл 🤔",
            "Попробуй другое слово — например «словарь», «функция», «декоратор».",
        )
    lines = [f"{topic_emoji(h.lesson.topic)} {h.lesson.title}" for h in hits]
    return _join(
        f"🔍 <b>Поиск: «{safe}»</b>",
        f"Нашёл тем: {len(hits)}",
        "\n".join(lines),
        "Открой тему 👇",
    )


def bookmarks_list(items) -> str:
    if not items:
        return _join(
            "⭐ <b>Избранное</b>",
            "Здесь пока пусто.",
            "Открой любую тему и нажми ⭐ — она появится тут для быстрого доступа.",
        )
    lines = [f"{topic_emoji(b.lesson.topic)} {b.lesson.title}" for b in items]
    return _join("⭐ <b>Избранное</b>", f"Сохранено тем: {len(items)}", "\n".join(lines), "Открой тему 👇")


def recommendations(recs) -> str:
    if not recs:
        return _join(
            "🧠 <b>Рекомендации</b>",
            "Начни с 📚 <b>Курсов</b> — и я подскажу, что почитать дальше.",
        )
    blocks = [f"{topic_emoji(r.lesson.topic)} <b>{r.lesson.title}</b>\n<i>{r.reason}</i>" for r in recs]
    return _join("🧠 <b>Что почитать дальше</b>", "\n\n".join(blocks), "Открой тему 👇")


def practice_warmup(lesson: Lesson) -> str:
    quiz = lesson.practice
    assert quiz is not None
    parts = [f"🔬 <b>Практика · {lesson.title}</b>", "Лёгкая разминка перед тестом 💪", quiz.question]
    if quiz.code:
        parts.append(_code_block(quiz.code))
    parts.append("Твой ответ? 👇")
    return _join(*parts)


def practice_warmup_result(lesson: Lesson, correct: bool) -> str:
    quiz = lesson.practice
    assert quiz is not None
    if correct:
        head = "✅ <b>Размялись!</b>"
    else:
        head = f"🤔 Не совсем. Правильный ответ: <b>{html.escape(quiz.options[quiz.correct])}</b>"
    return _join(head, f"💡 {quiz.explanation}", "Теперь основной тест 👇")


def lesson_quiz(lesson: Lesson) -> str:
    quiz = lesson.quiz
    parts = [f"🧪 <b>Мини-тест: {lesson.title}</b>", quiz.question]
    if quiz.code:
        parts.append(_code_block(quiz.code))
    parts.append("Выбери правильный ответ 👇")
    return _join(*parts)


def stage_complete(stage: Stage, reward: str, activity: ActivityResult | None,
                   course: "Course | None" = None) -> str:
    """A milestone celebration shown when the last lesson of a stage is passed."""
    course = course or get_course()
    skills = "\n".join(f"✅ {lesson.title}" for lesson in stage.lessons)
    next_stage = course.stage(stage.id + 1)

    # Identity badge for advanced (Student) blocks.
    ident = course_service.identity_for_stage(stage.id) if course.track == "student" else None
    badge = f"🎖 Получен титул: <b>{ident[0]} {ident[1]}</b>" if ident else ""

    if next_stage is not None:
        unlock = f"🔓 Открыт <b>Этап {next_stage.id}: {next_stage.title}</b>!"
        tail = "Идём дальше? 🚀"
    else:
        unlock = "Это был финальный этап — ты прошёл <b>весь курс</b>! 🐍🏆"
        tail = ""
    return _join(
        "🎉🏆 <b>Этап завершён!</b>",
        f"Ты только что прошёл «<b>{stage.title}</b>» 🔥",
        badge,
        f"<b>Теперь ты умеешь:</b>\n{skills}",
        reward,
        _activity_feedback(activity),
        unlock,
        tail,
    )


def lesson_result(lesson: Lesson, result: CompleteResult, wrong_attempts: int = 0,
                  course: "Course | None" = None) -> str:
    course = course or get_course()
    quiz = lesson.quiz
    reward = (
        f"⚡ <b>+{result.xp_gain} XP</b>"
        if result.awarded
        else "✅ Урок уже пройден — XP не начисляется."
    )

    # Milestone: finished the last lesson of a stage → big celebration.
    stage = course.stage(lesson.stage_id)
    if result.awarded and stage is not None and lesson.id == stage.last_id:
        return stage_complete(stage, reward, result.activity, course)

    adaptive = f"🎒 Запомни: {lesson.association}" if wrong_attempts > 0 else ""
    completed = "🏆 <b>Урок пройден!</b>" if result.awarded else ""
    has_next = lesson.id < course.total
    tail = "Идём дальше? 🚀" if has_next else "Ты прошёл весь курс — это вершина! 🐍🏆"
    challenge_hint = "Хочешь бонус? Жми ⚡ <b>Challenge</b>." if lesson.challenge else ""
    return _join(
        flavor.praise(),
        f"💡 {quiz.explanation}",
        adaptive,
        completed,
        reward,
        flavor.maybe_motivation(),
        _activity_feedback(result.activity),
        challenge_hint,
        tail,
    )


def challenge_card(lesson: Lesson) -> str:
    quiz = lesson.challenge
    assert quiz is not None
    parts = [
        "⚡ <b>Challenge — бонус</b>",
        "Задание чуть сложнее, но ты справишься 💪",
        quiz.question,
    ]
    if quiz.code:
        parts.append(_code_block(quiz.code))
    parts.append("Выбери ответ 👇")
    return _join(*parts)


def challenge_result(lesson: Lesson, activity: ActivityResult) -> str:
    quiz = lesson.challenge
    assert quiz is not None
    has_next = lesson.id < total_lessons()
    tail = "Идём дальше? 🚀" if has_next else "Ты прошёл весь курс целиком! 🐍🏆"
    return _join(
        "🔥 <b>Challenge пройден!</b>",
        f"💡 {quiz.explanation}",
        f"⚡ <b>+{CHALLENGE_XP} XP</b>",
        _activity_feedback(activity),
        tail,
    )


# ─────────────────────────────── Practice ─────────────────────────────────

def practice_intro() -> str:
    return (
        "🧪 <b>Practice Mode</b>\n\n"
        "Выбери категорию и прокачай навык. За каждый правильный ответ — XP ⚡\n\n"
        "Сложность: 🟢 Easy · 🟡 Medium · 🔴 Hard\n\n"
        "Выбирай тему 👇"
    )


def practice_pick_difficulty(topic: str) -> str:
    return f"{topic_emoji(topic)} <b>{topic_name(topic)}</b>\n\nВыбери сложность 👇"


def practice_question(question: Quiz, difficulty: str) -> str:
    parts = [f"🧪 <b>Практика · {DIFFICULTY_NAMES.get(difficulty, difficulty)}</b>", question.question]
    if question.code:
        parts.append(_code_block(question.code))
    parts.append("Твой ответ? 👇")
    return _join(*parts)


def practice_result(answer: PracticeAnswer) -> str:
    question = answer.question
    if answer.correct:
        head = flavor.praise()
        reward = f"⚡ <b>+{answer.xp_gain} XP</b>"
        motivation = flavor.maybe_motivation(0.4)
    else:
        correct_text = question.options[question.correct] if question else "?"
        head = f"❌ <b>Мимо!</b>\nПравильный ответ: <b>{html.escape(correct_text)}</b>"
        reward = ""
        motivation = ""
    explanation = f"💡 {question.explanation}" if question else ""
    return _join(head, explanation, reward, motivation, _activity_feedback(answer.activity), "Ещё разок? 👇")


# ────────────────────────────── Code Practice ─────────────────────────────

def code_intro() -> str:
    return (
        "💻 <b>Code Practice</b>\n\n"
        "Здесь ты пишешь <b>настоящий код</b> и присылаешь его сообщением — "
        "я проверю его по-настоящему (разбором синтаксиса, без запуска).\n\n"
        "Выбери тему 👇\n"
        "<i>🔒 — доступно в PRO</i>"
    )


def code_task_card(task: CodeTask) -> str:
    return _join(
        f"💻 <b>Code · {topic_emoji(task.topic)} {topic_name(task.topic)}</b> · "
        f"{DIFFICULTY_NAMES.get(task.difficulty, task.difficulty)}",
        f"📝 <b>Задача:</b>\n{task.prompt}",
        f"💡 <i>Подсказка:</i>\n{_code_block(task.hint)}",
        "✍️ Напиши код и пришли его <b>сообщением</b>.",
    )


def code_pass(result: CodeResult) -> str:
    return _join(
        flavor.praise(),
        "🏆 <b>Задача решена!</b>",
        result.task.success,
        f"⚡ <b>+{result.xp_gain} XP</b>",
        _activity_feedback(result.activity),
        "Готов к следующей? 👇",
    )


def code_fail(result: CodeResult) -> str:
    return _join(
        "🤔 <b>Почти!</b>",
        result.check.message,
        f"💡 <i>Подсказка:</i>\n{_code_block(result.task.hint)}",
        "Поправь и пришли код снова 👇",
    )


# ──────────────────── Code Runner (sandbox) + Debug ───────────────────────

def sandbox_intro() -> str:
    return (
        "🧪 <b>Тренажёр кода</b>\n\n"
        "Пиши настоящие функции — я запущу их в <b>безопасной песочнице</b> "
        "и прогоню через скрытые тесты (включая граничные случаи).\n\n"
        "🎯 <b>Адаптивная задача</b> подберёт следующую под твой уровень.\n"
        "Или выбери тему вручную 👇"
    )


def sandbox_topic_intro(topic: str) -> str:
    return _join(
        f"{topic_emoji(topic)} <b>{topic_name(topic)}</b>",
        "✅ решено · 🟢 easy · 🟡 medium · 🔴 hard · 🔒 PRO",
        "Выбери задачу 👇",
    )


def sandbox_adaptive_card(task, reason: str) -> str:
    return _join(f"🎯 <b>Подобрано:</b> {reason}", sandbox_task_card(task))


def sandbox_task_card(task) -> str:
    examples = "\n".join(task.examples)
    return _join(
        f"🧪 <b>{task.func}()</b> · {DIFFICULTY_NAMES.get(task.difficulty, task.difficulty)}",
        task.prompt,
        f"<b>Сигнатура:</b>\n{_code_block(task.signature)}",
        f"<b>Примеры:</b>\n{examples}" if examples else "",
        "✍️ Пришли решение <b>сообщением</b> — целиком функцию.",
    )


def sandbox_pass(outcome) -> str:
    badge = "🥇 С первой попытки!" if outcome.first_try else ""
    return _join(
        "🎉 <b>Решено!</b>",
        badge,
        f"✅ Пройдено тестов: {outcome.result.total}/{outcome.result.total}",
        f"⚡ <b>+{outcome.xp_gain} XP</b>",
        _activity_feedback(outcome.activity),
        "Готов к следующей? 👇",
    )


def sandbox_fail(outcome) -> str:
    hint = outcome.task.hints[0] if outcome.task.hints else ""
    return _join(
        sandbox.feedback(outcome.result),
        f"💡 <i>Подсказка:</i> {hint}" if hint else "",
        "Поправь и пришли код снова 👇",
    )


def debug_intro() -> str:
    return (
        "🛠 <b>Разбор бага</b>\n\n"
        "Пришли свой сломанный код — объясню, <b>что</b> пошло не так, <b>почему</b> "
        "и как думать над фиксом. Запускаю в песочнице, без вреда.\n\n"
        "Пришли код сообщением 👇"
    )


def debug_result(result) -> str:
    stdout_block = f"🖨 Вывод:\n{_code_block(result.stdout)}" if result.stdout.strip() else ""
    if result.status == "passed":
        return _join(
            "✅ <b>Код выполнился без ошибок.</b>",
            stdout_block,
            "Если результат всё равно не тот — опиши, что ожидал получить.",
        )
    return _join(
        sandbox.feedback(result),
        stdout_block,
        "💭 Подумай: на каком шаге значение становится не таким, как ты ждёшь?",
    )


# ────────────────────────────── Backend Projects ──────────────────────────

_PROJECT_DIFF_LABEL = {"easy": "🟢 Лёгкий", "medium": "🟡 Средний", "hard": "🔴 Сложный"}
_PROJECT_DIFF_ICON = {"easy": "🟢", "medium": "🟡", "hard": "🔴"}


def projects_intro(statuses) -> str:
    lines = []
    for st in statuses:
        icon = _PROJECT_DIFF_ICON.get(st.project.difficulty, "⚪")
        tier = "" if st.project.tier == "free" else " 💎"
        state = "✅ готов" if st.finished else (f"{st.percent}%" if st.step > 0 else "—")
        lines.append(f"{st.project.emoji} <b>{st.project.title}</b> {icon}{tier} · {state}")
    return _join(
        "🚀 <b>Backend-проекты</b>",
        "Портфолио-проекты с пошаговым гайдом. Доводишь до конца — получаешь XP "
        "и реальный проект, который не стыдно показать на собесе.",
        "\n".join(lines),
        "🎁 Первый проект — бесплатный. Выбери проект 👇",
    )


def project_card(status) -> str:
    p = status.project
    diff = _PROJECT_DIFF_LABEL.get(p.difficulty, p.difficulty)
    steps = []
    for i, step in enumerate(p.steps):
        icon = "✅" if i < status.step else ("▶️" if i == status.step else "🔒")
        steps.append(f"{icon} {i + 1}. {step.title}")
    if status.finished:
        tail = "🏁 <b>Проект завершён</b> — добавляй в портфолио!"
    else:
        tail = (f"{progress_bar(status.done_steps, status.total)} {status.percent}%   ·   "
                f"⚡ {p.total_xp} XP за проект")
        if p.tier == "pro":
            tail += "\n💎 <i>Прохождение шагов — в PRO</i>"
    return _join(
        f"{p.emoji} <b>{p.title}</b>  ·  {diff}",
        p.summary,
        f"🧩 <b>Стек:</b> {' · '.join(p.stack)}",
        f"🎯 <b>Результат:</b> {p.outcome}",
        "<b>Шаги:</b>\n" + "\n".join(steps),
        tail,
    )


def project_step(project, index: int) -> str:
    step = project.steps[index]
    return _join(
        f"{project.emoji} <b>{project.title}</b>",
        f"<b>Шаг {index + 1}/{project.total_steps}: {step.title}</b>",
        f"🎯 <b>Цель:</b> {step.goal}",
        step.detail,
        f"📦 <b>Результат шага:</b> {step.deliverable}",
        f"⚡ За шаг: <b>+{step.xp} XP</b>",
        "Сделал? Жми ✅ <b>Готово, дальше</b> 👇",
    )


def project_complete(project, activity) -> str:
    return _join(
        "🏆🎉 <b>Проект завершён!</b>",
        f"Ты собрал <b>{project.title}</b> {project.emoji} — это реальный пункт в портфолио.",
        f"⚡ Всего за проект: <b>+{project.total_xp} XP</b>",
        _activity_feedback(activity),
        f"🎯 {project.outcome}",
        "Готов к следующему вызову? 🚀",
    )


def project_step_result(result) -> str:
    if result.finished:
        return project_complete(result.project, result.activity)
    step = result.completed
    return _join(
        f"✅ <b>Шаг готов:</b> {step.title}",
        f"⚡ <b>+{result.xp_gain} XP</b>",
        _activity_feedback(result.activity),
        f"Дальше — шаг {result.new_step + 1}/{result.project.total_steps}. Погнали 👇",
    )


# ─────────────────────────── Smart Coach ──────────────────────────────────

def coach(r) -> str:
    identity = f"🎖 Ранг: {r.identity[0]} <b>{r.identity[1]}</b>" if r.identity else ""
    return _join(
        "🧠 <b>Smart Coach</b>",
        identity,
        f"🛤 <b>Путь в Junior Backend</b>\n{progress_bar(r.readiness, 100)} {r.readiness}%\n"
        f"{r.tier_emoji} <b>{r.tier_label}</b>",
        ("<b>Из чего складывается:</b>\n"
         f"📚 Программа: {r.coverage_pct}%\n"
         f"🎯 Точность: {r.accuracy_pct}%\n"
         f"🧠 Освоено тем: {r.mastery_pct}%\n"
         f"🔥 Постоянство: {r.streak_days} дн."),
        f"💪 Силён: {', '.join(r.strengths)}" if r.strengths else "💪 Сильные темы появятся после практики",
        f"🧩 Подтянуть: {', '.join(r.weaknesses)}" if r.weaknesses else "",
        r.focus,
        f"🟢 Beginner {r.beginner_pct}% · 🟣 Student {r.student_pct}%",
    )


# ──────────────────────────────── Daily ───────────────────────────────────

def daily_card(challenge: Quiz) -> str:
    parts = [
        "📅 <b>Daily Python Challenge</b>",
        "Задача дня. Реши и получи XP + бонус за streak 🔥",
        challenge.question,
    ]
    if challenge.code:
        parts.append(_code_block(challenge.code))
    parts.append("Твой ответ? 👇")
    return _join(*parts)


def daily_already_done(user) -> str:
    return (
        "📅 <b>Daily Challenge</b>\n\n"
        "✅ На сегодня задача уже решена — красава! 🔥\n\n"
        f"🔥 Streak: <b>{user.streak}</b>\n"
        "Новая задача будет завтра. А пока загляни в 💻 Code Practice 👇"
    )


def daily_result(result: DailyResult, challenge: Quiz) -> str:
    bonus = f"🔥 +{result.bonus_xp} streak-бонус" if result.bonus_xp else ""
    return _join(
        "🎉 <b>Daily выполнен!</b>",
        f"💡 {challenge.explanation}",
        f"⚡ <b>+{result.base_xp} XP</b>\n{bonus}".strip(),
        flavor.maybe_motivation(),
        _activity_feedback(result.activity),
        "Возвращайся завтра за новой задачей! 📅",
    )


# ─────────────────────────────── Leaderboard ──────────────────────────────

def leaderboard(board: Leaderboard) -> str:
    medals = ["🥇", "🥈", "🥉"]
    if not board.rows:
        body = "Здесь пока пусто 🌱\nРеши урок или Daily — и твоё имя появится тут первым! 🥇"
    else:
        lines = []
        for i, row in enumerate(board.rows):
            place = medals[i] if i < 3 else f"<b>{i + 1}.</b>"
            name = html.escape(row.username or "Аноним")
            lines.append(f"{place} {name} — ⚡{row.weekly_xp} · 🔥{row.streak}")
        body = "\n".join(lines)

    if board.my_weekly_xp > 0:
        me_line = f"📍 Ты: <b>#{board.my_rank}</b> · ⚡ {board.my_weekly_xp} XP за неделю"
    else:
        me_line = "📍 Ты ещё не в гонке — заработай XP сегодня и попади в топ! 🚀"

    return _join(
        "🏆 <b>Рейтинг недели</b>",
        f"<i>Неделя {board.week_key}</i>",
        body,
        me_line,
        "XP недели обнуляется в понедельник — успей в топ! 💪",
    )


# ─────────────────────────── Profile & achievements ───────────────────────

def profile(user, level: LevelInfo, lessons_read: int, total_all: int,
            bookmarks_count: int, tracks: list[tuple[str, int]] | None = None) -> str:
    """Theory-hub profile: reading progress, streak, level, favourites."""
    name = html.escape(user.username or "питонист")
    tracks_block = ""
    if tracks:
        tracks_block = "📚 <b>Курсы:</b>\n" + "\n".join(f"{label} — {pct}%" for label, pct in tracks)

    streak_line = (
        f"🔥 Дней подряд: <b>{user.streak}</b> (рекорд {user.best_streak})"
        if user.streak > 0
        else "🔥 Дней подряд: <b>0</b> — заходи каждый день за новой темой"
    )
    return _join(
        f"👤 <b>{name}</b>",
        (
            f"🧠 <b>{level.title}</b> · Level {level.level}\n"
            f"{level.bar} {level.percent}%"
        ),
        (
            f"📖 Прочитано тем: <b>{lessons_read}</b> из {total_all}\n"
            f"⭐ В избранном: <b>{bookmarks_count}</b>\n"
            f"{streak_line}"
        ),
        tracks_block,
        "Продолжай в своём темпе — понимание важнее скорости 📚",
    )


def achievements(status: list[tuple[Achievement, bool]]) -> str:
    unlocked = sum(1 for _, owned in status if owned)
    lines = []
    for ach, owned in status:
        mark = "✅" if owned else "🔒"
        lines.append(f"{mark} {ach.emoji} <b>{ach.title}</b> — {ach.description}")
    return (
        "🏆 <b>Достижения</b>\n\n"
        f"Открыто: <b>{unlocked}/{len(status)}</b>\n\n"
        f"{chr(10).join(lines)}\n\n"
        "Каждое достижение — ещё один повод вернуться 😉"
    )


# ─────────────────────────── Monetization (PRO) ───────────────────────────

def upsell(reason: str = "") -> str:
    perks = "\n".join(f"• <b>{label}</b> — {blurb}" for label, blurb in feature_service.PRO_PERKS)
    return _join(
        "✨ <b>Python Academy PRO</b>",
        reason,
        f"В PRO открывается:\n{perks}",
        "💎 Оплата подключается скоро. А пока доступ можно получить у администратора.",
    )


def practice_limit_reached(limit: int) -> str:
    return (
        "🚦 <b>Дневной лимит практики</b>\n\n"
        f"На сегодня бесплатные <b>{limit}</b> ответов закончились — "
        "мозгу полезно отдохнуть 😊\n\n"
        "Возвращайся завтра или открой <b>PRO</b> для безлимита ♾️"
    )


# ─────────────────────── Premium offer · sales screens ─────────────────────

# Seed social proof — REPLACE with real student testimonials before launch.
_TESTIMONIALS = (
    "«За 2 месяца собрал 3 проекта и прошёл собес на Junior» — Артём",
    "«Наконец-то понял backend, а не просто посмотрел видео» — Лена",
    "«Сертификат + проекты в резюме = первые отклики от HR» — Дмитрий",
)

PAYMENTS_OFF_ALERT = ("Оплата пока не включена. Доступ можно получить у администратора — "
                      "напиши ему, и он откроет PRO.")
PURCHASE_UNKNOWN = "Платёж получен, но продукт не распознан 🤔 Напиши администратору — всё поправим."


def offer(is_pro: bool = False) -> str:
    if is_pro:
        return _join(
            "💎 <b>У тебя PRO — полный доступ</b>",
            "Открыто всё: проекты, проверка кода, именной сертификат и Career Path.",
            "🎁 Поделись ботом по своей ссылке — друг получит 7 дней PRO, а ты +30 дней за его покупку.",
            "Спасибо, что поддерживаешь проект 💜",
        )
    prices = "\n".join(
        f"• <b>{p.title}</b> — {p.stars}⭐ <i>({p.price_label})</i>\n  {p.blurb}"
        for p in pricing.PRODUCTS
    )
    proof = "\n".join(f"⭐️ {t}" for t in _TESTIMONIALS)
    return _join(
        "🚀 <b>Из «прошёл курс» — в Junior-разработчика</b>",
        "Бесплатно — вся теория. В <b>PRO</b> начинается то, за что платят на собесах:",
        ("✅ <b>Реальные проекты</b> в портфолио (Todo API, авторизация, деплой)\n"
         "✅ <b>Проверка кода</b> в песочнице — мгновенный разбор ошибок\n"
         "✅ <b>Именной сертификат</b> о прохождении\n"
         "✅ <b>Career Path</b> — измеримый путь до Junior с дорожной картой\n"
         "✅ Новые курсы и обновления — без доплат"),
        f"<b>Тарифы:</b>\n{prices}",
        f"<b>Что говорят ученики:</b>\n{proof}",
        "🔒 Оплата проходит безопасно внутри Telegram (Stars).",
        "Выбери доступ 👇",
    )


def purchase_success(product) -> str:
    return _join(
        "🎉 <b>Оплата прошла — добро пожаловать в PRO!</b>",
        f"Тариф: <b>{product.title}</b>.",
        ("Теперь открыто:\n"
         "🚀 Проекты в портфолио\n"
         "🧪 Проверка кода\n"
         "🎓 Сертификаты\n"
         "🎯 Career Path"),
        "🎁 Позови друга по своей ссылке — получишь <b>+30 дней PRO</b> за его покупку!",
        "Поехали 👇",
    )


def invite(link: str, invited: int, converted: int, reward_days: int, welcome_days: int) -> str:
    link_block = (
        f"🔗 Твоя ссылка:\n<code>{link}</code>"
        if link else "🔗 Ссылка появится, когда бот будет запущен под своим именем."
    )
    return _join(
        "🎁 <b>Приглашай друзей — получай PRO</b>",
        f"За каждого друга, который оформит PRO, ты получаешь <b>+{reward_days} дней</b> доступа.",
        f"А твой друг стартует с <b>{welcome_days} днями PRO</b> в подарок 🎉",
        link_block,
        f"👥 Приглашено: <b>{invited}</b>   ·   💎 Оформили PRO: <b>{converted}</b>",
        "Скопируй ссылку и отправь тому, кто тоже хочет в IT 🚀",
    )


def career(report) -> str:
    bar = progress_bar(report.readiness, 100)
    roadmap = "\n".join(
        f"{'✅' if m.done else '▫️'} {m.label} — {m.percent}%" for m in report.milestones
    )
    return _join(
        "🎯 <b>Career Path → Junior Python Backend</b>",
        "Твоя цель: собрать портфолио и выйти на первую работу. Вот где ты сейчас:",
        f"{bar} <b>{report.readiness}%</b>\n{report.tier_emoji} <b>{report.tier_label}</b>",
        f"<b>Дорожная карта:</b>\n{roadmap}",
        f"🛠 Проекты: <b>{report.projects_done}/{report.projects_total}</b>   ·   🔥 рекорд серии: {report.streak_days}",
        report.next_step,
    )


def certificate_locked(course_title: str, completed: bool) -> str:
    if completed:
        return _join(
            f"🎓 <b>Сертификат · {course_title}</b>",
            "Ты прошёл курс целиком — поздравляю! 🎉",
            "Именной сертификат с уникальным кодом выдаётся в <b>PRO</b>.",
            "Это артефакт в резюме и LinkedIn — открой PRO и забери свой 👇",
        )
    return _join(
        f"🎓 <b>Сертификат · {course_title}</b>",
        "Сертификат выдаётся за <b>полное прохождение курса</b> (все темы прочитаны).",
        "Дочитай курс до конца — и забери именной сертификат 💪",
    )


def certificate_card(cert, newly: bool = False) -> str:
    head = "🎉 <b>Сертификат выдан!</b>" if newly else "🎓 <b>Твой сертификат</b>"
    return _join(
        head,
        f"<b>{cert.course_title}</b>",
        f"Владелец: <b>{html.escape(cert.holder)}</b>\n"
        f"Дата: <b>{cert.issued}</b>\n"
        f"Код проверки: <code>{cert.code}</code>",
        "Поделись достижением — кнопкой ниже 👇",
    )


def certificate_share(cert) -> str:
    """Plain shareable text (forwardable)."""
    return (
        f"🎓 Я прошёл курс «{cert.course_title}» в Python Academy!\n"
        f"Сертификат № {cert.code} от {cert.issued}.\n"
        f"Учу Python с нуля 🐍 #PythonAcademy"
    )


# ─────────────────────────── Admin analytics ──────────────────────────────

def admin_headline(a) -> str:
    """Compact product KPIs appended to the /admin overview."""
    return _join(
        "📊 <b>Аналитика</b>",
        f"🔁 D1: <b>{a.d1_pct}%</b> ({a.d1_num}/{a.d1_den}) · "
        f"D7: <b>{a.d7_pct}%</b> ({a.d7_num}/{a.d7_den})",
        f"💰 FREE→PRO: <b>{a.conversion_pct}%</b> ({a.pro_users}/{a.total_users}) · "
        f"🚪 лимит сегодня: <b>{a.paywall_hits}</b>",
        f"💻 Решено задач: <b>{a.tasks_solved}</b> · учеников {a.task_solvers}",
        "Детали: <code>/analytics</code>",
    )


def admin_analytics(a) -> str:
    hardest = "\n".join(
        f"{i}. {name} — {acc}% ({att})" for i, (name, acc, att) in enumerate(a.hardest, 1)
    ) or "— мало данных"
    skipped = "\n".join(
        f"{i}. {name} — {att} ответов" for i, (name, att) in enumerate(a.most_skipped, 1)
    ) or "—"
    dropoff = "\n".join(f"• {label} — <b>{count}</b>" for label, count in a.dropoff) or "—"
    funnel = "\n".join(f"• {label}: <b>{n}</b>" for label, n in a.funnel) or "—"
    return _join(
        "📊 <b>Аналитика · детали</b>",
        f"🔥 <b>Самые сложные темы</b> (по точности):\n{hardest}",
        f"🥶 <b>Реже всего практикуют</b>:\n{skipped}",
        f"🚪 <b>Где застревают (drop-off)</b>:\n{dropoff}",
        f"📈 <b>Воронка прохождения</b>:\n{funnel}",
        f"🔁 Retention D1 <b>{a.d1_pct}%</b> · D7 <b>{a.d7_pct}%</b>   ·   "
        f"💰 Конверсия <b>{a.conversion_pct}%</b>",
    )


# ──────────────────────────────── Alerts ──────────────────────────────────

LOCKED_LESSON_ALERT = "🔒 Сначала пройди предыдущий урок!"
STAGE_LOCKED_ALERT = "🔒 Сначала заверши предыдущий этап!"
WRONG_ANSWER_ALERT = "❌ Не совсем! Попробуй ещё раз 👇"
WRONG_ANSWER_HINT = "🎒 Подсказка: вспомни ассоциацию из урока и попробуй снова."
STALE_BUTTON_ALERT = "Эта кнопка больше не активна 🤷"
IN_LESSON_HINT = "👀 Используй кнопки под уроком, чтобы продолжить 👇"
USE_BUTTONS_HINT = "🤖 Я понимаю кнопки лучше слов 😄 Вот главное меню 👇"
PRO_LOCKED_ALERT = "🔒 Это доступно в PRO"
