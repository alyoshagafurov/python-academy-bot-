"""Load learning content from JSON into dataclasses.

A course is a directory `content/<lang>/<track>/` containing:
  • course.json  — metadata + ordered list of stage file names
  • stage_*.json — a stage with its lessons

Global lesson ids are assigned sequentially across stages, so the rest of the
app can keep treating progress as a single growing number.
"""
from __future__ import annotations

import json
from pathlib import Path

from lessons.schema import (
    CodeTask, CodingTask, Course, Lesson, Project, ProjectStep, Quiz, Snippet, Stage,
)

CONTENT_DIR = Path(__file__).resolve().parent.parent / "content"


def _quiz(data: dict | None) -> Quiz | None:
    if not data:
        return None
    return Quiz(
        question=data["question"],
        options=tuple(data["options"]),
        correct=int(data["correct"]),
        explanation=data.get("explanation", ""),
        code=data.get("code", ""),
        topic=data.get("topic", ""),
    )


def _lesson(data: dict, lesson_id: int, stage_id: int) -> Lesson:
    return Lesson(
        id=lesson_id,
        stage_id=stage_id,
        topic=data.get("topic", ""),
        title=data["title"],
        theory=data.get("theory", ""),
        association=data.get("association", ""),
        real_example=data.get("real_example", ""),
        example=data.get("example", ""),
        code_explained=data.get("code_explained", ""),
        common_mistakes=tuple(data.get("common_mistakes", ())),
        practice=_quiz(data.get("practice")),
        quiz=_quiz(data.get("quiz")),
        challenge=_quiz(data.get("challenge")),
        xp=int(data.get("xp", 20)),
        placeholder=bool(data.get("placeholder", False)),
    )


def load_course(course_dir: Path) -> Course:
    meta = json.loads((course_dir / "course.json").read_text(encoding="utf-8"))

    stages: list[Stage] = []
    counter = 1  # global lesson id
    for stage_file in meta["stages"]:
        sdata = json.loads((course_dir / f"{stage_file}.json").read_text(encoding="utf-8"))
        lessons: list[Lesson] = []
        for lesson_data in sdata.get("lessons", []):
            lessons.append(_lesson(lesson_data, counter, sdata["id"]))
            counter += 1
        stages.append(Stage(
            id=int(sdata["id"]),
            title=sdata["title"],
            subtitle=sdata.get("subtitle", ""),
            emoji=sdata.get("emoji", "📍"),
            lessons=tuple(lessons),
        ))

    return Course(
        id=meta["id"],
        language=meta["language"],
        track=meta["track"],
        title=meta["title"],
        emoji=meta["emoji"],
        stages=tuple(stages),
        description=meta.get("description", ""),
    )


def load_courses() -> dict[str, Course]:
    """Discover every course (a `course.json` under content/<lang>/<track>/)."""
    courses: dict[str, Course] = {}
    for meta_file in sorted(CONTENT_DIR.glob("*/*/course.json")):
        try:
            course = load_course(meta_file.parent)
        except (json.JSONDecodeError, OSError, KeyError):
            continue
        courses[course.id] = course
    return courses


def load_code_tasks(path: Path) -> tuple[CodeTask, ...]:
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    return tuple(
        CodeTask(
            id=task["id"],
            topic=task["topic"],
            difficulty=task.get("difficulty", "easy"),
            tier=task.get("tier", "free"),
            prompt=task["prompt"],
            hint=task.get("hint", ""),
            checks=tuple(task["checks"]),
            success=task.get("success", ""),
            xp=int(task.get("xp", 10)),
        )
        for task in data["tasks"]
    )


def load_coding_tasks(path: Path) -> tuple[CodingTask, ...]:
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    return tuple(
        CodingTask(
            id=task["id"],
            topic=task["topic"],
            difficulty=task.get("difficulty", "easy"),
            tier=task.get("tier", "free"),
            prompt=task["prompt"],
            func=task["func"],
            signature=task.get("signature", ""),
            examples=tuple(task.get("examples", ())),
            tests=tuple(tuple(case) for case in task["tests"]),
            hints=tuple(task.get("hints", ())),
            xp=int(task.get("xp", 15)),
            solution=task.get("solution", ""),
        )
        for task in data["tasks"]
    )


def load_snippets(path: Path) -> tuple[Snippet, ...]:
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    return tuple(
        Snippet(
            id=snip["id"],
            category=snip["category"],
            title=snip["title"],
            description=snip.get("description", ""),
            difficulty=snip.get("difficulty", "easy"),
            code=snip["code"],
            tip=snip.get("tip", ""),
        )
        for snip in data["snippets"]
    )


def load_projects(path: Path) -> tuple[Project, ...]:
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    return tuple(
        Project(
            id=proj["id"],
            title=proj["title"],
            emoji=proj.get("emoji", "🚀"),
            difficulty=proj.get("difficulty", "medium"),
            tier=proj.get("tier", "pro"),
            summary=proj.get("summary", ""),
            stack=tuple(proj.get("stack", ())),
            outcome=proj.get("outcome", ""),
            steps=tuple(
                ProjectStep(
                    title=step["title"],
                    goal=step.get("goal", ""),
                    detail=step.get("detail", ""),
                    deliverable=step.get("deliverable", ""),
                    xp=int(step.get("xp", 30)),
                )
                for step in proj.get("steps", [])
            ),
        )
        for proj in data["projects"]
    )
