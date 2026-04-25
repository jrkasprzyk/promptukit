#!/usr/bin/env python3
"""Add questions to a question bank.

Interactive mode:
  python -m promptukit.questions.add_question path/to/bank.json
  python -m promptukit.questions.add_question --type TrueFalse path/to/bank.json
  python -m promptukit.questions.add_question --create path/to/new-bank.json

Batch mode reads a JSON array of partial question objects from a file or
stdin, auto-assigns IDs, and appends to the bank without prompts:
  python -m promptukit.questions.add_question --batch questions.json path/to/bank.json
  cat questions.json | python -m promptukit.questions.add_question --batch - path/to/bank.json

Every batch object needs category, difficulty, and prompt. The
``question_type`` field selects type-specific required fields (see
``BATCH_TYPE_REQUIRED`` below); if omitted, the type is inferred from the
shape of the object. Optional on all types: quip_correct, quip_wrong. IDs
are auto-generated; any ``id`` field in the input is ignored.
"""

from __future__ import annotations

import argparse
import io
import json
import sys
from pathlib import Path
from typing import Any

from promptukit.utils.cli_helpers import confirm, load, pick, save
from promptukit.utils.json_tools import infer_question_type

DIFFICULTIES = ["easy", "medium", "hard"]
QUESTION_TYPES = (
    "MultipleChoice",
    "TrueFalse",
    "ShortAnswer",
    "FillInTheBlank",
    "Matching",
    "Calculation",
)

QUESTION_TYPE_ALIASES = {
    "mc": "MultipleChoice",
    "mcq": "MultipleChoice",
    "multiple_choice": "MultipleChoice",
    "multiplechoice": "MultipleChoice",
    "true_false": "TrueFalse",
    "truefalse": "TrueFalse",
    "tf": "TrueFalse",
    "short": "ShortAnswer",
    "short_answer": "ShortAnswer",
    "shortanswer": "ShortAnswer",
    "fill": "FillInTheBlank",
    "fill_blank": "FillInTheBlank",
    "fill_in_the_blank": "FillInTheBlank",
    "fillintheblank": "FillInTheBlank",
    "fitb": "FillInTheBlank",
    "match": "Matching",
    "matching": "Matching",
    "calc": "Calculation",
    "calculation": "Calculation",
    "numeric": "Calculation",
}

BATCH_COMMON_REQUIRED = {"category", "difficulty", "prompt"}

BATCH_TYPE_REQUIRED: dict[str, set[str]] = {
    "MultipleChoice": {"choices", "answer"},
    "TrueFalse": {"answer"},
    "ShortAnswer": {"answer"},
    "FillInTheBlank": {"answers"},
    "Matching": {"pairs"},
    "Calculation": {"answer"},
}

BATCH_TYPE_FIELDS: dict[str, tuple[str, ...]] = {
    "MultipleChoice": ("choices", "answer"),
    "TrueFalse": ("answer",),
    "ShortAnswer": ("answer",),
    "FillInTheBlank": ("answers",),
    "Matching": ("pairs",),
    "Calculation": ("answer", "tolerance", "unit"),
}

# Kept for backward compatibility; older callers may import this.
BATCH_REQUIRED = BATCH_COMMON_REQUIRED | BATCH_TYPE_REQUIRED["MultipleChoice"]


def normalize_question_type(value: str) -> str | None:
    """Return the canonical question type for a CLI value or alias."""
    key = value.strip().replace("-", "_").replace(" ", "_").lower()
    return QUESTION_TYPE_ALIASES.get(key)


def _type_help() -> str:
    return ", ".join(QUESTION_TYPES) + " (aliases: mcq, tf, short, fill_blank, matching, numeric)"


def _load_bank(bank_path: Path, *, create_missing: bool = False) -> dict[str, Any]:
    """Load a bank dict, or create an empty one when explicitly requested."""
    try:
        data = load(bank_path)
    except FileNotFoundError:
        if not create_missing:
            raise
        bank_path.parent.mkdir(parents=True, exist_ok=True)
        return {"categories": [], "questions": []}

    if not isinstance(data, dict):
        raise ValueError("bank JSON must be an object with a 'questions' array")

    data.setdefault("categories", [])
    data.setdefault("questions", [])
    if not isinstance(data["categories"], list):
        raise ValueError("bank 'categories' must be an array")
    if not isinstance(data["questions"], list):
        raise ValueError("bank 'questions' must be an array")
    return data


# ---------------------------------------------------------------------------
# Helpers
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
        print("    (required - please enter a value)")


def prompt_optional(label: str) -> str:
    return input(f"  {label}: ").strip()


def prompt_bool(label: str) -> bool:
    true_values = {"true", "t", "yes", "y", "1"}
    false_values = {"false", "f", "no", "n", "0"}
    while True:
        raw = input(f"  {label} (true/false): ").strip().lower()
        if raw in true_values:
            return True
        if raw in false_values:
            return False
        print("    Please enter true or false.")


def prompt_number(label: str, *, required: bool = True) -> int | float | None:
    while True:
        raw = input(f"  {label}: ").strip()
        if not raw and not required:
            return None
        try:
            value = float(raw)
        except ValueError:
            print("    Please enter a number.")
            continue
        if value.is_integer() and "." not in raw and "e" not in raw.lower():
            return int(raw)
        return value


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
        return questions + [new_q]
    return questions[: last_idx + 1] + [new_q] + questions[last_idx + 1:]


def preview(q: dict) -> None:
    qtype = q.get("question_type", "MultipleChoice")
    print("\n  Preview")
    print("  " + "-" * 58)
    print(f"  id            : {q['id']}")
    print(f"  question_type : {qtype}")
    print(f"  category      : {q['category']}")
    print(f"  difficulty    : {q['difficulty']}")
    print(f"  prompt        : {q['prompt']}")

    if qtype == "MultipleChoice":
        ans = q.get("answer")
        for i, choice in enumerate(q.get("choices", [])):
            marker = "*" if i == ans else " "
            print(f"  {marker} [{i}] {choice}")
    elif qtype == "TrueFalse":
        print(f"  answer        : {q.get('answer')}")
    elif qtype == "ShortAnswer":
        print(f"  answer        : {q.get('answer')!r}")
    elif qtype == "FillInTheBlank":
        for i, answer in enumerate(q.get("answers", [])):
            print(f"    blank[{i}]    : {answer!r}")
    elif qtype == "Matching":
        for i, pair in enumerate(q.get("pairs", [])):
            print(f"    pair[{i}]     : {pair[0]!r} -> {pair[1]!r}")
    elif qtype == "Calculation":
        print(f"  answer        : {q.get('answer')}")
        if q.get("tolerance") is not None:
            print(f"  tolerance     : {q['tolerance']}")
        if q.get("unit"):
            print(f"  unit          : {q['unit']}")

    if q.get("quip_correct"):
        print(f"  quip_correct  : {q['quip_correct']}")
    if q.get("quip_wrong"):
        print(f"  quip_wrong    : {q['quip_wrong']}")
    print("  " + "-" * 58)


# ---------------------------------------------------------------------------
# Interactive flow
# ---------------------------------------------------------------------------

def collect_category(categories: list[str]) -> str:
    """Prompt for an existing or new category."""
    if not categories:
        print("  No categories defined - please create a new category.")
        category = prompt("New category name")
        categories.append(category)
        return category

    new_category_marker = "Create new category"
    choice = pick("Category", categories + [new_category_marker])
    if choice != new_category_marker:
        return choice

    category = prompt("New category name")
    if category not in categories:
        categories.append(category)
    return category


def collect_question_type(question_type: str | None) -> str:
    if question_type:
        return question_type

    print("\n  Question type")
    for i, qtype in enumerate(QUESTION_TYPES, 1):
        print(f"    {i}) {qtype}")
    while True:
        raw = input("  Choice: ").strip()
        if raw.isdigit() and 1 <= int(raw) <= len(QUESTION_TYPES):
            return QUESTION_TYPES[int(raw) - 1]
        normalized = normalize_question_type(raw)
        if normalized:
            return normalized
        print("    Please enter a number or a supported type/alias.")


def collect_prompt(qtype: str) -> str:
    if qtype != "FillInTheBlank":
        return prompt("Prompt (the question text)")

    while True:
        value = prompt("Prompt (use ___ for each blank)")
        if value.count("___") > 0:
            return value
        print("    FillInTheBlank prompts need at least one ___ placeholder.")


def collect_multiple_choice() -> dict[str, Any]:
    print("\n  Enter the four answer choices:")
    choices = [prompt(f"Choice {letter}") for letter in "ABCD"]

    print("\n  Which choice is correct?")
    for i, (letter, text) in enumerate(zip("ABCD", choices)):
        print(f"    {i}) {letter} - {text}")
    while True:
        raw = input("  Answer (0-3 or A-D): ").strip()
        if raw in ("0", "1", "2", "3"):
            return {"choices": choices, "answer": int(raw)}
        upper = raw.upper()
        if upper in ("A", "B", "C", "D"):
            return {"choices": choices, "answer": ord(upper) - ord("A")}
        print("    Please enter 0, 1, 2, 3, A, B, C, or D.")


def collect_fill_in_the_blank(prompt_text: str) -> dict[str, Any]:
    blanks = prompt_text.count("___")
    print(f"\n  Detected {blanks} blank(s).")
    answers = [prompt(f"Answer for blank {i + 1}") for i in range(blanks)]
    return {"answers": answers}


def collect_matching() -> dict[str, Any]:
    print("\n  Enter matching pairs. Each pair is stored as [left, right].")
    pairs: list[list[str]] = []
    while True:
        left = prompt(f"Pair {len(pairs) + 1} left")
        right = prompt(f"Pair {len(pairs) + 1} right")
        pairs.append([left, right])
        if not confirm("Add another pair?"):
            break
    return {"pairs": pairs}


def collect_calculation() -> dict[str, Any]:
    answer = prompt_number("Answer")
    tolerance = prompt_number("Tolerance (optional, blank for none)", required=False)
    unit = prompt_optional("Unit (optional)")
    fields: dict[str, Any] = {"answer": answer}
    if tolerance is not None:
        fields["tolerance"] = tolerance
    if unit:
        fields["unit"] = unit
    return fields


def collect_type_fields(qtype: str, prompt_text: str) -> dict[str, Any]:
    if qtype == "MultipleChoice":
        return collect_multiple_choice()
    if qtype == "TrueFalse":
        return {"answer": prompt_bool("Answer")}
    if qtype == "ShortAnswer":
        return {"answer": prompt("Answer")}
    if qtype == "FillInTheBlank":
        return collect_fill_in_the_blank(prompt_text)
    if qtype == "Matching":
        return collect_matching()
    if qtype == "Calculation":
        return collect_calculation()
    raise ValueError(f"unsupported question_type: {qtype}")


def collect_question(categories: list[str], questions: list[dict], *, question_type: str | None = None) -> dict:
    print("\n" + "=" * 62)
    print("  NEW QUESTION")
    print("=" * 62)

    category = collect_category(categories)
    difficulty = pick("Difficulty", DIFFICULTIES)
    qtype = collect_question_type(question_type)

    print()
    prompt_text = collect_prompt(qtype)
    type_fields = collect_type_fields(qtype, prompt_text)

    print("\n  Quips are optional - press Enter to skip.")
    quip_correct = prompt_optional("quip_correct")
    quip_wrong = prompt_optional("quip_wrong")

    q: dict[str, Any] = {
        "id": next_id(questions, category),
        "question_type": qtype,
        "category": category,
        "difficulty": difficulty,
        "prompt": prompt_text,
    }
    q.update(type_fields)
    if quip_correct:
        q["quip_correct"] = quip_correct
    if quip_wrong:
        q["quip_wrong"] = quip_wrong
    return q


# ---------------------------------------------------------------------------
# Batch mode
# ---------------------------------------------------------------------------

def _load_batch(source: str) -> list[dict]:
    """Read a JSON array of partial question objects from a file path or '-'."""
    if source == "-":
        raw = sys.stdin.read()
    else:
        raw = Path(source).read_text(encoding="utf-8-sig")
    data = json.loads(raw)
    if not isinstance(data, list):
        raise ValueError("Batch input must be a JSON array of question objects")
    return data


def _resolve_batch_question_type(raw: dict[str, Any]) -> str:
    qtype = raw.get("question_type")
    if isinstance(qtype, str):
        normalized = normalize_question_type(qtype)
        if normalized:
            return normalized
        return qtype
    return infer_question_type(raw)


def cmd_batch(bank_path: Path, batch_source: str, *, create_missing: bool = False) -> int:
    print(f"Loading bank: {bank_path}")
    try:
        data = _load_bank(bank_path, create_missing=create_missing)
    except FileNotFoundError:
        print(f"FATAL: bank not found: {bank_path}")
        print("Pass --create to create a new bank.")
        return 1
    except json.JSONDecodeError as e:
        print(f"FATAL: invalid JSON in bank - {e}")
        return 1
    except ValueError as e:
        print(f"FATAL: invalid bank - {e}")
        return 1

    try:
        incoming = _load_batch(batch_source)
    except (json.JSONDecodeError, ValueError) as e:
        print(f"FATAL: invalid batch input - {e}")
        return 1
    except FileNotFoundError as e:
        print(f"FATAL: {e}")
        return 1

    questions: list[dict] = data["questions"]
    categories: list[str] = data["categories"]
    initial_categories = list(categories)
    added = 0
    errors = 0

    for i, raw in enumerate(incoming):
        if not isinstance(raw, dict):
            print(f"  SKIP item[{i}]: expected object")
            errors += 1
            continue

        missing_common = BATCH_COMMON_REQUIRED - set(raw.keys())
        if missing_common:
            print(f"  SKIP item[{i}]: missing fields {missing_common}")
            errors += 1
            continue

        qtype = _resolve_batch_question_type(raw)
        if qtype not in BATCH_TYPE_REQUIRED:
            print(f"  SKIP item[{i}]: unsupported question_type '{qtype}'")
            errors += 1
            continue

        missing_type = BATCH_TYPE_REQUIRED[qtype] - set(raw.keys())
        if missing_type:
            print(f"  SKIP item[{i}] [{qtype}]: missing fields {missing_type}")
            errors += 1
            continue

        cat = raw["category"]
        if cat not in categories:
            print(f"  Adding new category: {cat}")
            categories.append(cat)

        q: dict[str, Any] = {
            "id": next_id(questions, cat),
            "question_type": qtype,
            "category": cat,
            "difficulty": raw["difficulty"],
            "prompt": raw["prompt"],
        }
        for field in BATCH_TYPE_FIELDS[qtype]:
            if field in raw:
                q[field] = raw[field]
        for opt in ("quip_correct", "quip_wrong"):
            if raw.get(opt):
                q[opt] = raw[opt]

        preview(q)
        questions = insert_after_category(questions, q)
        added += 1

    data["questions"] = questions
    if added or categories != initial_categories:
        data["categories"] = categories
        save(bank_path, data)

    print(f"\nDone. {added} question(s) added, {errors} skipped.")
    return 0 if not errors else 1


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main(argv: list[str] | None = None) -> int:
    if isinstance(sys.stdout, io.TextIOWrapper):
        try:
            sys.stdout.reconfigure(encoding="utf-8")
        except (AttributeError, ValueError, io.UnsupportedOperation):
            pass

    p = argparse.ArgumentParser(description="Add questions to a question bank")
    p.add_argument("bank", help="Path to the question bank JSON")
    p.add_argument(
        "--batch",
        metavar="FILE",
        help="Batch mode: read a JSON array of questions from FILE (use '-' for stdin)",
    )
    p.add_argument(
        "--type",
        dest="question_type",
        help=f"Interactive question type. Supported: {_type_help()}",
    )
    p.add_argument(
        "--create",
        action="store_true",
        help="Create an empty bank if BANK does not exist",
    )
    args = p.parse_args(argv)

    question_type = None
    if args.question_type:
        question_type = normalize_question_type(args.question_type)
        if question_type is None:
            p.error(f"unsupported --type {args.question_type!r}; supported: {_type_help()}")

    bank_path = Path(args.bank)
    if args.batch:
        return cmd_batch(bank_path, args.batch, create_missing=args.create)

    print(f"Loading: {bank_path}")
    try:
        data = _load_bank(bank_path, create_missing=args.create)
    except FileNotFoundError:
        print(f"FATAL: bank not found: {bank_path}")
        print("Pass --create to create a new bank.")
        return 1
    except json.JSONDecodeError as e:
        print(f"FATAL: invalid JSON - {e}")
        return 1
    except ValueError as e:
        print(f"FATAL: invalid bank - {e}")
        return 1

    categories: list[str] = data["categories"]
    questions: list[dict] = data["questions"]

    added = 0
    while True:
        q = collect_question(categories, questions, question_type=question_type)
        preview(q)

        if confirm("Save this question?"):
            questions = insert_after_category(questions, q)
            data["questions"] = questions
            data["categories"] = categories
            save(bank_path, data)
            added += 1
            print(f"\n  Saved - {q['id']} added ({len(questions)} questions total).")
        else:
            print("\n  Discarded.")

        if not confirm("Add another question?"):
            break

    print(f"\nDone. {added} question(s) added.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
