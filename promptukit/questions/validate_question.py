#!/usr/bin/env python3
"""Validate a question bank JSON file.

Dispatches per ``question_type`` (see
``promptukit.questions.question_models``) so every supported type is
checked with its own structural rules. Untagged questions are classified
via ``infer_question_type``.

Common checks apply to all types: required id/category/difficulty/prompt,
duplicate ids, known category, known difficulty, and placeholder text in
the prompt.
"""

import json
import sys
from collections import Counter
from pathlib import Path
from typing import Any

from promptukit.utils.json_tools import flatten_questions, infer_question_type

DEFAULT_BANK_PATH = Path(__file__).resolve().parent.parent / "data" / "question_banks" / "block-doku-questions.json"

BLOCK_DOKU_CATEGORIES = {"motorsport", "music", "film-and-tv", "general", "meta", "asia", "books", "science and math", "linguistics", "pop"}
VALID_DIFFICULTIES = {"easy", "medium", "hard"}

COMMON_REQUIRED = {"id", "category", "difficulty", "prompt"}

TYPE_REQUIRED: dict[str, set[str]] = {
    "MultipleChoice": {"choices", "answer"},
    "TrueFalse":      {"answer"},
    "ShortAnswer":    {"answer"},
    "FillInTheBlank": {"answers"},
    "Matching":       {"pairs"},
    "Calculation":    {"answer"},
}


def load(path: Path) -> dict:
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def _valid_categories(data: dict) -> set[str]:
    """Return the set of allowed categories for this file.

    Uses the file's top-level ``"categories"`` list when present,
    otherwise falls back to the block-doku hardcoded set.
    """
    declared = data.get("categories")
    if declared and isinstance(declared, list):
        return set(declared)
    return BLOCK_DOKU_CATEGORIES


# ---------------------------------------------------------------------------
# Per-type structural checks
# ---------------------------------------------------------------------------

def _check_mcq(q: dict, label: str, errors: list[str], warnings: list[str]) -> None:
    choices = q.get("choices")
    if not isinstance(choices, list) or len(choices) != 4:
        errors.append(f"{label} [MultipleChoice]: choices must be an array of exactly 4 strings")
        return
    ans = q.get("answer")
    # Accept int 0-3, single letter A-D, or exact choice text
    if isinstance(ans, int):
        if ans not in range(4):
            errors.append(f"{label} [MultipleChoice]: answer must be int 0-3, got {ans}")
    elif isinstance(ans, str):
        if len(ans) == 1 and ans.upper() in "ABCD":
            pass
        elif ans in choices:
            pass
        else:
            errors.append(f"{label} [MultipleChoice]: answer string '{ans}' is neither a letter A-D nor a choice text")
    else:
        errors.append(f"{label} [MultipleChoice]: answer must be int 0-3, letter A-D, or choice text; got {ans!r}")

    if any(isinstance(c, str) and ("Option A" in c or "Option B" in c) for c in choices):
        warnings.append(f"{label} [MultipleChoice]: choices look like placeholders (Option A/B)")


def _check_true_false(q: dict, label: str, errors: list[str], warnings: list[str]) -> None:
    ans = q.get("answer")
    if isinstance(ans, bool):
        return
    if isinstance(ans, str) and ans.strip().lower() in ("true", "false"):
        warnings.append(f"{label} [TrueFalse]: answer is string {ans!r}; prefer a real JSON boolean")
        return
    errors.append(f"{label} [TrueFalse]: answer must be a boolean, got {ans!r}")


def _check_short_answer(q: dict, label: str, errors: list[str], warnings: list[str]) -> None:
    ans = q.get("answer")
    if not isinstance(ans, str):
        errors.append(f"{label} [ShortAnswer]: answer must be a string, got {ans!r}")
        return
    if not ans.strip():
        errors.append(f"{label} [ShortAnswer]: answer is empty")


def _check_fill_in_the_blank(q: dict, label: str, errors: list[str], warnings: list[str]) -> None:
    answers = q.get("answers")
    if not isinstance(answers, list) or not answers:
        errors.append(f"{label} [FillInTheBlank]: answers must be a non-empty list")
        return
    if not all(isinstance(a, str) and a.strip() for a in answers):
        errors.append(f"{label} [FillInTheBlank]: every answer must be a non-empty string")
    prompt_text = q.get("prompt") or ""
    blanks = prompt_text.count("___")
    if blanks != len(answers):
        errors.append(
            f"{label} [FillInTheBlank]: prompt has {blanks} '___' blank(s) but answers has {len(answers)} entry(ies)"
        )


def _check_matching(q: dict, label: str, errors: list[str], warnings: list[str]) -> None:
    pairs = q.get("pairs")
    if not isinstance(pairs, list) or not pairs:
        errors.append(f"{label} [Matching]: pairs must be a non-empty list")
        return
    shape_ok = True
    lefts: list[str] = []
    rights: list[str] = []
    for i, p in enumerate(pairs):
        if not (isinstance(p, list) and len(p) == 2
                and isinstance(p[0], str) and p[0].strip()
                and isinstance(p[1], str) and p[1].strip()):
            errors.append(f"{label} [Matching]: pair[{i}] must be a 2-element list of non-empty strings")
            shape_ok = False
        else:
            lefts.append(p[0])
            rights.append(p[1])
    if not shape_ok:
        return
    if len(pairs) < 3 or len(pairs) > 6:
        warnings.append(f"{label} [Matching]: {len(pairs)} pair(s); 3-6 is the typical range")
    if len(set(lefts)) != len(lefts):
        errors.append(f"{label} [Matching]: left-column items are not all distinct")
    if len(set(rights)) != len(rights):
        errors.append(f"{label} [Matching]: right-column items are not all distinct")


def _check_calculation(q: dict, label: str, errors: list[str], warnings: list[str]) -> None:
    ans = q.get("answer")
    if isinstance(ans, bool) or not isinstance(ans, (int, float)):
        errors.append(f"{label} [Calculation]: answer must be a number, got {ans!r}")
    tol = q.get("tolerance")
    if tol is not None:
        if isinstance(tol, bool) or not isinstance(tol, (int, float)):
            errors.append(f"{label} [Calculation]: tolerance must be a number, got {tol!r}")
        elif tol < 0:
            errors.append(f"{label} [Calculation]: tolerance must be non-negative, got {tol}")
    unit = q.get("unit")
    if unit is not None and not isinstance(unit, str):
        errors.append(f"{label} [Calculation]: unit must be a string, got {unit!r}")


_VALIDATORS = {
    "MultipleChoice": _check_mcq,
    "TrueFalse":      _check_true_false,
    "ShortAnswer":    _check_short_answer,
    "FillInTheBlank": _check_fill_in_the_blank,
    "Matching":       _check_matching,
    "Calculation":    _check_calculation,
}


# ---------------------------------------------------------------------------
# Validation entry point
# ---------------------------------------------------------------------------

def validate(data: Any) -> tuple[list[str], list[str]]:
    errors: list[str] = []
    warnings: list[str] = []

    questions = flatten_questions(data)
    if not questions:
        errors.append("No questions found (expected top-level 'questions' array or category-mapped shape)")
        return errors, warnings

    valid_categories = (
        _valid_categories(data) if isinstance(data, dict) else BLOCK_DOKU_CATEGORIES
    )
    ids_seen: set[str] = set()

    for i, q in enumerate(questions):
        label = q.get("id", f"questions[{i}]")

        # --- common required fields ---
        missing = COMMON_REQUIRED - set(q.keys())
        if missing:
            errors.append(f"{label}: missing fields {missing}")
            continue

        # --- duplicate IDs ---
        if q["id"] in ids_seen:
            errors.append(f"{label}: duplicate id")
        ids_seen.add(q["id"])

        # --- category / difficulty ---
        if q["category"] not in valid_categories:
            errors.append(f"{label}: unknown category '{q['category']}' (not in file's categories list)")
        if q["difficulty"] not in VALID_DIFFICULTIES:
            errors.append(f"{label}: unknown difficulty '{q['difficulty']}'")

        # --- placeholder detection (all types) ---
        if isinstance(q.get("prompt"), str) and "EXAMPLE" in q["prompt"].upper():
            errors.append(f"{label}: still contains EXAMPLE placeholder text")

        # --- dispatch to type-specific checks ---
        qtype = q.get("question_type") or infer_question_type(q)
        type_required = TYPE_REQUIRED.get(qtype, set())
        missing_type_fields = type_required - set(q.keys())
        if missing_type_fields:
            errors.append(f"{label} [{qtype}]: missing fields {missing_type_fields}")
            continue

        checker = _VALIDATORS.get(qtype)
        if checker is None:
            warnings.append(f"{label}: unknown question_type '{qtype}' — skipping structural checks")
            continue
        checker(q, label, errors, warnings)

    return errors, warnings


# ---------------------------------------------------------------------------
# Stats
# ---------------------------------------------------------------------------

def print_stats(data: Any) -> None:
    questions = flatten_questions(data)
    if not questions:
        print("\n  (no questions to summarize)")
        return

    types = Counter(q.get("question_type") or infer_question_type(q) for q in questions)
    cats = Counter(q.get("category", "(none)") for q in questions)
    diffs = Counter(q.get("difficulty", "(none)") for q in questions)

    print(f"\n  Total questions: {len(questions)}")

    print("\n  By question_type:")
    for t in ("MultipleChoice", "TrueFalse", "ShortAnswer", "FillInTheBlank", "Matching", "Calculation"):
        if types.get(t, 0):
            print(f"    {t:<16} {types.get(t, 0)}")
    other = sum(v for k, v in types.items() if k not in _VALIDATORS)
    if other:
        print(f"    (other)          {other}")

    declared = data.get("categories") if isinstance(data, dict) else None
    display_cats = declared if (declared and isinstance(declared, list)) else sorted(cats.keys())

    print("\n  By category:")
    for cat in display_cats:
        print(f"    {cat:<24} {cats.get(cat, 0)}")

    print("\n  By difficulty:")
    for diff in ("easy", "medium", "hard"):
        print(f"    {diff:<12} {diffs.get(diff, 0)}")

    # MCQ answer distribution — only over MCQ questions
    mcq = [q for q in questions
           if (q.get("question_type") or infer_question_type(q)) == "MultipleChoice"]
    if mcq:
        answers: Counter = Counter()
        for q in mcq:
            ans = q.get("answer")
            if isinstance(ans, int):
                answers[ans] += 1
            elif isinstance(ans, str) and len(ans) == 1 and ans.upper() in "ABCD":
                answers[ord(ans.upper()) - ord("A")] += 1
            elif isinstance(ans, str):
                choices = q.get("choices") or []
                if ans in choices:
                    answers[choices.index(ans)] += 1

        print(f"\n  MCQ answer distribution (n={len(mcq)}; 0=A, 1=B, 2=C, 3=D):")
        for idx in range(4):
            letter = "ABCD"[idx]
            count = answers.get(idx, 0)
            pct = 100 * count / len(mcq) if mcq else 0
            bar = "#" * count
            print(f"    {letter} ({idx}): {count:>3} ({pct:4.1f}%)  {bar}")

        expected = len(mcq) / 4
        for idx in range(4):
            count = answers.get(idx, 0)
            if count > expected * 1.6:
                letter = "ABCD"[idx]
                print(f"\n  WARNING: MCQ answer {letter} is overrepresented ({count}/{len(mcq)})")

    # TrueFalse balance
    tf = [q for q in questions
          if (q.get("question_type") or infer_question_type(q)) == "TrueFalse"]
    if tf:
        t_count = sum(1 for q in tf if q.get("answer") is True)
        f_count = sum(1 for q in tf if q.get("answer") is False)
        print(f"\n  TrueFalse balance (n={len(tf)}):")
        print(f"    true   {t_count}")
        print(f"    false  {f_count}")
        if tf and (t_count == 0 or f_count == 0 or max(t_count, f_count) / len(tf) > 0.75):
            print("\n  WARNING: TrueFalse bank is skewed (>75% one side)")


def main() -> int:
    path = Path(sys.argv[1]) if len(sys.argv) > 1 else DEFAULT_BANK_PATH
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
