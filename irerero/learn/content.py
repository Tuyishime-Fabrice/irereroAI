"""The four LEARN courses from content/courses/<course_id>/: course.json, lessons/NN.md and
quiz.json (five questions). Lesson text is a placeholder citing its source until the team
finalises it; Kinyarwanda titles are drafts until reviewed."""

import json
from pathlib import Path

import pandas as pd

from irerero.config import CONTENT

COURSES = CONTENT / "courses"
PASS_MARK = 0.8  # 4 of 5 questions


def load(root: Path = COURSES) -> dict[str, pd.DataFrame]:
    courses, lessons, quiz = [], [], []
    for folder in sorted(p for p in root.iterdir() if p.is_dir()):
        meta = json.loads((folder / "course.json").read_text())
        course_id = folder.name
        courses.append(
            {
                "course_id": course_id,
                "position": meta["position"],
                "title_en": meta["title_en"],
                "title_rw": meta["title_rw"],
                "required_on_joining": meta["required_on_joining"],
                "trigger": meta["trigger"],
                "source": meta["source"],
            }
        )
        files = sorted((folder / "lessons").glob("*.md"))
        if not 3 <= len(files) <= 5:
            raise ValueError(f"{course_id}: needs 3 to 5 lessons, found {len(files)}")
        for position, file in enumerate(files, start=1):
            body = file.read_text()
            title = body.splitlines()[0].lstrip("# ").strip()
            lessons.append(
                {
                    "id": f"{course_id}-{position}",
                    "course_id": course_id,
                    "position": position,
                    "title": title,
                    "body_md": body,
                }
            )
        items = json.loads((folder / "quiz.json").read_text())["items"]
        if len(items) != 5:
            raise ValueError(f"{course_id}: the quiz needs 5 questions, found {len(items)}")
        for position, item in enumerate(items, start=1):
            if not 0 <= item["answer"] < len(item["options"]):
                raise ValueError(f"{course_id} question {position}: answer out of range")
            quiz.append(
                {
                    "id": f"{course_id}-q{position}",
                    "course_id": course_id,
                    "position": position,
                    "question": item["question"],
                    "options": item["options"],
                    "answer": item["answer"],
                }
            )
    return {
        "course": pd.DataFrame(courses).sort_values("position"),
        "lesson": pd.DataFrame(lessons),
        "quiz_item": pd.DataFrame(quiz),
    }
