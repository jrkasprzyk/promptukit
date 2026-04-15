#!/usr/bin/env python3
"""Validate assets/trivia.json for schema correctness, answer distribution, and content quality."""

import json
import sys
from collections import Counter
from pathlib import Path

TRIVIA_PATH = Path(__file__).resolve().parent.parent / "assets" / "trivia.json"

VALID_CATEGORIES = {"motorsport", "music", "film-and-tv", "general", "meta", "asia", "books", "science and math", "linguistics", "pop"}
VALID_DIFFICULTIES = {"easy", "medium", "hard"}
REQUIRED_FIELDS = {"id", "category", "difficulty", "prompt", "choices", "answer"}


def load(path: Path) -> dict:
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def validate(data: dict) -> list[str]:
    errors: list[str] = []
    warnings: list[str] = []

    if "questions" not in data:
        errors.append("Missing top-level 'questions' array")
        return errors

    questions = data["questions"]
    ids_seen: set[str] = set()

    for i, q in enumerate(questions):
        label = q.get("id", f"questions[{i}]")

        # --- required fields ---
        missing = REQUIRED_FIELDS - set(q.keys())
        if missing:
            errors.append(f"{label}: missing fields {missing}")
            continue

        # --- duplicate IDs ---
        if q["id"] in ids_seen:
            errors.append(f"{label}: duplicate id")
        ids_seen.add(q["id"])

        # --- category / difficulty ---
        if q["category"] not in VALID_CATEGORIES:
            errors.append(f"{label}: unknown category '{q['category']}'")
        if q["difficulty"] not in VALID_DIFFICULTIES:
            errors.append(f"{label}: unknown difficulty '{q['difficulty']}'")

        # --- choices ---
        if not isinstance(q["choices"], list) or len(q["choices"]) != 4:
            errors.append(f"{label}: choices must be an array of exactly 4 strings")
            continue

        # --- answer index ---
        if not isinstance(q["answer"], int) or q["answer"] not in range(4):
            errors.append(f"{label}: answer must be int 0-3, got {q['answer']}")

        # --- placeholder detection ---
        if "EXAMPLE" in q["prompt"].upper():
            errors.append(f"{label}: still contains EXAMPLE placeholder text")
        if any("Option A" in c or "Option B" in c for c in q["choices"]):
            warnings.append(f"{label}: choices look like placeholders (Option A/B)")

    return errors, warnings


def print_stats(data: dict) -> None:
    questions = data["questions"]
    cats = Counter(q["category"] for q in questions)
    diffs = Counter(q["difficulty"] for q in questions)
    answers = Counter(q["answer"] for q in questions)

    print(f"\n  Total questions: {len(questions)}")

    print("\n  By category:")
    for cat in sorted(VALID_CATEGORIES):
        print(f"    {cat:<12} {cats.get(cat, 0)}")

    print("\n  By difficulty:")
    for diff in ["easy", "medium", "hard"]:
        print(f"    {diff:<12} {diffs.get(diff, 0)}")

    print("\n  Answer distribution (0=A, 1=B, 2=C, 3=D):")
    for idx in range(4):
        letter = "ABCD"[idx]
        count = answers.get(idx, 0)
        pct = 100 * count / len(questions) if questions else 0
        bar = "#" * count
        print(f"    {letter} ({idx}): {count:>2} ({pct:4.1f}%)  {bar}")

    # flag skewed distribution
    if questions:
        expected = len(questions) / 4
        for idx in range(4):
            count = answers.get(idx, 0)
            if count > expected * 1.6:
                letter = "ABCD"[idx]
                print(f"\n  WARNING: answer {letter} is overrepresented ({count}/{len(questions)})")


def main() -> int:
    path = Path(sys.argv[1]) if len(sys.argv) > 1 else TRIVIA_PATH
    print(f"Validating: {path}")

    try:
        data = load(path)
    except json.JSONDecodeError as e:
        print(f"\n  FATAL: invalid JSON — {e}")
        return 1

    errors, warnings = validate(data)
    print_stats(data)

    if warnings:
        print(f"\n  {len(warnings)} warning(s):")
        for w in warnings:
            print(f"    WARN: {w}")

    if errors:
        print(f"\n  {len(errors)} error(s):")
        for e in errors:
            print(f"    ERROR: {e}")
        return 1

    print("\n  All checks passed.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
