#!/usr/bin/env python3
"""Add questions to a question bank.

Interactive mode (default):
  python -m promptukit.questions.add_question [path/to/bank.json]

Batch mode — read a JSON array of partial question objects from a file or
stdin, auto-assign IDs, and append to the bank without any prompts:
  python -m promptukit.questions.add_question --batch questions.json [path/to/bank.json]
  cat questions.json | python -m promptukit.questions.add_question --batch - [path/to/bank.json]

Each object in the batch array must have: category, difficulty, prompt,
choices (4 strings), answer (0-3 int).  Optional: quip_correct, quip_wrong.
IDs are auto-generated; any "id" field in the input is ignored.
"""

import io
import sys
import json
import argparse
from pathlib import Path

from promptukit.utils.cli_helpers import load, save, pick, confirm

DEFAULT_BANK_PATH = Path(__file__).resolve().parent.parent.parent / "content" / "question_banks" / "block-doku-questions.json"
DIFFICULTIES = ["easy", "medium", "hard"]


# ---------------------------------------------------------------------------
# Helpers (shared helpers imported from cli_helpers)
# ---------------------------------------------------------------------------

def prompt(label: str, *, default: str = "") -> str:
    """Read a non-empty string from stdin."""
    suffix = f" [{default}]" if default else ""
    while True:
        value = input(f"  {label}{suffix}: ").strip()
        if not value and default:
            return default
        if value:
            return value
        print("    (required — please enter a value)")


def next_id(questions: list[dict], category: str) -> str:
    """Return the next unused id for a category, e.g. motorsport_014."""
    existing = [
        q["id"] for q in questions
        if q.get("id", "").startswith(f"{category}_")
    ]
    nums = []
    for qid in existing:
        suffix = qid[len(category) + 1:]
        if suffix.isdigit():
            nums.append(int(suffix))
    next_num = (max(nums) + 1) if nums else 1
    return f"{category}_{next_num:03d}"


def insert_after_category(questions: list[dict], new_q: dict) -> list[dict]:
    """Insert new_q after the last question that shares its category."""
    cat = new_q["category"]
    last_idx = -1
    for i, q in enumerate(questions):
        if q.get("category") == cat:
            last_idx = i
    if last_idx == -1:
        # New category — append at end
        return questions + [new_q]
    return questions[: last_idx + 1] + [new_q] + questions[last_idx + 1 :]


def preview(q: dict) -> None:
    print("\n  ┌─ Preview " + "─" * 50)
    print(f"  │  id         : {q['id']}")
    print(f"  │  category   : {q['category']}")
    print(f"  │  difficulty : {q['difficulty']}")
    print(f"  │  prompt     : {q['prompt']}")
    for i, choice in enumerate(q["choices"]):
        marker = "✓" if i == q["answer"] else " "
        print(f"  │  {marker} [{i}] {choice}")
    if q.get("quip_correct"):
        print(f"  │  quip_correct : {q['quip_correct']}")
    if q.get("quip_wrong"):
        print(f"  │  quip_wrong   : {q['quip_wrong']}")
    print("  └" + "─" * 59)


# ---------------------------------------------------------------------------
# Interactive flow
# ---------------------------------------------------------------------------

def collect_question(categories: list[str], questions: list[dict]) -> dict:
    print("\n" + "=" * 62)
    print("  NEW QUESTION")
    print("=" * 62)

    # Allow creating a new category interactively. If no categories exist,
    # prompt the user to create one immediately. Otherwise offer an extra
    # menu entry to create a new category.
    if not categories:
        print("  No categories defined — please create a new category.")
        category = prompt("New category name")
        categories.append(category)
    else:
        NEW_CATEGORY_MARKER = "Create new category"
        options = categories + [NEW_CATEGORY_MARKER]
        choice = pick("Category", options)
        if choice == NEW_CATEGORY_MARKER:
            new_cat = prompt("New category name")
            if new_cat not in categories:
                categories.append(new_cat)
            category = new_cat
        else:
            category = choice
    difficulty = pick("Difficulty", DIFFICULTIES)

    print()
    q_prompt = prompt("Prompt (the question text)")

    print("\n  Enter the four answer choices:")
    choices = []
    for letter in "ABCD":
        choices.append(prompt(f"  Choice {letter}"))

    print("\n  Which choice is correct?")
    for i, (letter, text) in enumerate(zip("ABCD", choices)):
        print(f"    {i}) {letter} — {text}")
    while True:
        raw = input("  Answer (0–3): ").strip()
        if raw in ("0", "1", "2", "3"):
            answer = int(raw)
            break
        print("    Please enter 0, 1, 2, or 3.")

    print("\n  Quips are optional — press Enter to skip.")
    quip_correct = input("  quip_correct: ").strip()
    quip_wrong = input("  quip_wrong  : ").strip()

    qid = next_id(questions, category)

    q: dict = {
        "id": qid,
        "category": category,
        "difficulty": difficulty,
        "prompt": q_prompt,
        "choices": choices,
        "answer": answer,
    }
    if quip_correct:
        q["quip_correct"] = quip_correct
    if quip_wrong:
        q["quip_wrong"] = quip_wrong

    return q


# `confirm` is provided by `cli_helpers` and imported above.


# ---------------------------------------------------------------------------
# Batch mode
# ---------------------------------------------------------------------------

BATCH_REQUIRED = {"category", "difficulty", "prompt", "choices", "answer"}


def _load_batch(source: str) -> list[dict]:
    """Read a JSON array of partial question objects from a file path or '-' for stdin."""
    if source == "-":
        raw = sys.stdin.read()
    else:
        raw = Path(source).read_text(encoding="utf-8")
    data = json.loads(raw)
    if not isinstance(data, list):
        raise ValueError("Batch input must be a JSON array of question objects")
    return data


def cmd_batch(bank_path: Path, batch_source: str) -> int:
    print(f"Loading bank: {bank_path}")
    try:
        data = load(bank_path)
    except json.JSONDecodeError as e:
        print(f"FATAL: invalid JSON in bank — {e}")
        return 1

    try:
        incoming = _load_batch(batch_source)
    except (json.JSONDecodeError, ValueError) as e:
        print(f"FATAL: invalid batch input — {e}")
        return 1
    except FileNotFoundError as e:
        print(f"FATAL: {e}")
        return 1

    questions: list[dict] = data.get("questions", [])
    categories: list[str] = data.get("categories", [])
    initial_categories = list(categories)
    added = 0
    errors = 0

    for i, raw in enumerate(incoming):
        missing = BATCH_REQUIRED - set(raw.keys())
        if missing:
            print(f"  SKIP item[{i}]: missing fields {missing}")
            errors += 1
            continue

        cat = raw["category"]
        if cat not in categories:
            print(f"  Adding new category: {cat}")
            categories.append(cat)

        qid = next_id(questions, cat)
        q: dict = {
            "id":         qid,
            "category":   cat,
            "difficulty": raw["difficulty"],
            "prompt":     raw["prompt"],
            "choices":    raw["choices"],
            "answer":     raw["answer"],
        }
        for opt in ("quip_correct", "quip_wrong"):
            if raw.get(opt):
                q[opt] = raw[opt]

        preview(q)
        questions = insert_after_category(questions, q)
        added += 1

    data["questions"] = questions
    # Save if questions added or categories were updated by the batch
    if added or categories != initial_categories:
        data["categories"] = categories
        save(bank_path, data)

    print(f"\nDone. {added} question(s) added, {errors} skipped.")
    return 0 if not errors else 1


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> int:
    if isinstance(sys.stdout, io.TextIOWrapper):
        sys.stdout.reconfigure(encoding="utf-8")

    p = argparse.ArgumentParser(description="Add trivia questions to a question bank")
    p.add_argument("bank", nargs="?", default=str(DEFAULT_BANK_PATH), help="Path to the question bank JSON")
    p.add_argument(
        "--batch", metavar="FILE",
        help="Batch mode: read a JSON array of questions from FILE (use '-' for stdin)"
    )
    args = p.parse_args()

    bank_path = Path(args.bank)

    if args.batch:
        return cmd_batch(bank_path, args.batch)

    # --- interactive mode ---
    print(f"Loading: {bank_path}")
    try:
        data = load(bank_path)
    except json.JSONDecodeError as e:
        print(f"FATAL: invalid JSON — {e}")
        return 1

    categories: list[str] = data.get("categories", [])
    questions: list[dict] = data.get("questions", [])

    added = 0
    while True:
        q = collect_question(categories, questions)
        preview(q)

        if confirm("Save this question?"):
            questions = insert_after_category(questions, q)
            data["questions"] = questions
            # Persist any newly-added categories as well
            data["categories"] = categories
            save(bank_path, data)
            added += 1
            print(f"\n  Saved — {q['id']} added ({len(questions)} questions total).")
        else:
            print("\n  Discarded.")

        if not confirm("Add another question?"):
            break

    print(f"\nDone. {added} question(s) added.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
