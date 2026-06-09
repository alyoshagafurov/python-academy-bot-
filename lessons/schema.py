"""Content schema — the in-memory shape of all learning content.

Hierarchy:  Course → Stage → Lesson  (+ Quiz, CodeTask)

Content lives in `content/<lang>/<track>/` (course.json + stage_*.json). Adding
a stage, lesson or whole new course means editing JSON — no code changes.
`Course.lessons` / `.get()` / `.total` flatten the stages so existing callers
that think in terms of a single lesson sequence keep working.
"""
from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class Quiz:
    question: str
    options: tuple[str, ...]
    correct: int          # index into `options`
    explanation: str
    code: str = ""        # optional snippet shown above the options
    topic: str = ""       # canonical topic key (see utils.constants)


@dataclass(frozen=True)
class Lesson:
    id: int                            # GLOBAL sequence number (assigned by loader)
    stage_id: int
    topic: str
    title: str
    theory: str = ""
    association: str = ""
    real_example: str = ""
    example: str = ""
    code_explained: str = ""
    common_mistakes: tuple[str, ...] = ()
    practice: Quiz | None = None       # warm-up (no XP)
    quiz: Quiz | None = None           # the test (gives lesson XP)
    challenge: Quiz | None = None      # bonus (gives bonus XP)
    xp: int = 20
    placeholder: bool = False          # structure-only lesson ("скоро")


@dataclass(frozen=True)
class Stage:
    id: int
    title: str
    subtitle: str
    emoji: str
    lessons: tuple[Lesson, ...] = field(default_factory=tuple)

    @property
    def total(self) -> int:
        return len(self.lessons)

    @property
    def first_id(self) -> int:
        return self.lessons[0].id if self.lessons else 0

    @property
    def last_id(self) -> int:
        return self.lessons[-1].id if self.lessons else 0

    @property
    def is_ready(self) -> bool:
        """A stage has real (non-placeholder) content."""
        return any(not lesson.placeholder for lesson in self.lessons)


@dataclass(frozen=True)
class Course:
    id: str
    language: str
    track: str
    title: str
    emoji: str
    stages: tuple[Stage, ...]
    description: str = ""   # short tagline for the course-selection screen

    @property
    def lessons(self) -> tuple[Lesson, ...]:
        return tuple(lesson for stage in self.stages for lesson in stage.lessons)

    @property
    def total(self) -> int:
        return len(self.lessons)

    def get(self, lesson_id: int) -> Lesson | None:
        for lesson in self.lessons:
            if lesson.id == lesson_id:
                return lesson
        return None

    def stage(self, stage_id: int) -> Stage | None:
        for stage in self.stages:
            if stage.id == stage_id:
                return stage
        return None

    def stage_of(self, lesson_id: int) -> Stage | None:
        for stage in self.stages:
            for lesson in stage.lessons:
                if lesson.id == lesson_id:
                    return stage
        return None


@dataclass(frozen=True)
class Snippet:
    """A ready-to-copy Minecraft+Python script (copy → paste in VS Code → run)."""

    id: str
    category: str        # buildings | effects | games | tools | art
    title: str
    description: str
    difficulty: str      # easy | medium | hard
    code: str
    tip: str = ""


@dataclass(frozen=True)
class CodeTask:
    """A 'write real code' task validated via AST (see services.code_check)."""

    id: str
    topic: str
    difficulty: str
    tier: str
    prompt: str
    hint: str
    checks: tuple[str, ...]
    success: str
    xp: int = 10


@dataclass(frozen=True)
class CodingTask:
    """A sandboxed coding task: user writes a function, hidden tests verify it."""

    id: str
    topic: str
    difficulty: str           # easy | medium | hard
    tier: str                 # free | pro
    prompt: str
    func: str                 # function the user must define
    signature: str            # display hint, e.g. "def sum_two(a, b):"
    examples: tuple[str, ...]  # visible examples
    tests: tuple              # ((args_list, expected), ...) incl. hidden edge cases
    hints: tuple[str, ...] = ()
    xp: int = 15
    solution: str = ""        # reference solution — used by tests only, never shown


@dataclass(frozen=True)
class ProjectStep:
    """One guided milestone inside a backend project."""

    title: str
    goal: str            # one-line objective
    detail: str          # what to do / how to think about it (HTML)
    deliverable: str     # what you should have built after this step
    xp: int = 30


@dataclass(frozen=True)
class Project:
    """A portfolio-worthy, multi-step backend build (guided, self-attested)."""

    id: str
    title: str
    emoji: str
    difficulty: str              # easy | medium | hard
    tier: str                    # free | pro
    summary: str
    stack: tuple[str, ...]
    outcome: str                 # what the learner walks away with
    steps: tuple[ProjectStep, ...] = ()

    @property
    def total_steps(self) -> int:
        return len(self.steps)

    @property
    def total_xp(self) -> int:
        return sum(step.xp for step in self.steps)
