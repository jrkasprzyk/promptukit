#!/usr/bin/env python3
"""Demo: migrate question banks and use the Question classes.

This script demonstrates:
- Inferring and adding `question_type` tags to legacy JSON
- Loading questions as typed Question objects
- Constructing each question type directly
- Serializing objects back to dicts (preserving raw JSON when requested)

Usage:
  python scripts/demo_question_usage.py [--bank PATH] [--out PATH] [--inplace] [--preserve-raw]

Defaults to using promptukit/data/question_banks/block-doku-sample.json
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any, Dict, List

from promptukit.utils.cli_helpers import load, save
from promptukit.utils.json_tools import add_question_type_tags, update_json_file, infer_question_type
from promptukit.questions.question_models import (
    Question,
    MultipleChoice,
    TrueFalse,
    ShortAnswer,
    FillInTheBlank,
    Matching,
    Calculation,
)


def _flatten_data(data: Any) -> List[Dict[str, Any]]:
    if isinstance(data, dict):
        if "questions" in data and isinstance(data["questions"], list):
            return [q for q in data["questions"] if isinstance(q, dict)]
        if all(isinstance(v, list) for v in data.values()):
            out: List[Dict[str, Any]] = []
            for v in data.values():
                if isinstance(v, list):
                    out.extend([q for q in v if isinstance(q, dict)])
            return out
        return [data]
    if isinstance(data, list):
        return [q for q in data if isinstance(q, dict)]
    return []


def _print_obj(label: str, obj: Question) -> None:
    print(f"  [{label}] {obj.question_type}: {obj.text}")
    d = obj.to_dict()
    for k, v in d.items():
        if k not in ("question_type", "prompt"):
            print(f"    {k}: {v}")


def _demo_new_types() -> None:
    print("\n--- New question type samples ---\n")

    mc = MultipleChoice(
        text="Which planet is closest to the Sun?",
        choices=["Venus", "Mercury", "Mars", "Earth"],
        answer=1,
    )
    _print_obj("MultipleChoice", mc)

    tf = TrueFalse(text="The Earth orbits the Moon.", answer=False)
    _print_obj("TrueFalse", tf)

    sa = ShortAnswer(text="What is the chemical symbol for gold?", answer="Au")
    _print_obj("ShortAnswer", sa)

    fitb = FillInTheBlank(
        text="The [blank] is the powerhouse of the cell.",
        answers=["mitochondria"],
    )
    _print_obj("FillInTheBlank", fitb)

    match = Matching(
        text="Match each element to its chemical symbol.",
        pairs=[["Hydrogen", "H"], ["Oxygen", "O"], ["Carbon", "C"]],
    )
    _print_obj("Matching", match)

    calc = Calculation(
        text="A car travels 150 km in 2 hours. What is its average speed?",
        answer=75.0,
        tolerance=0.5,
        unit="km/h",
    )
    _print_obj("Calculation", calc)
    print(f"    is_correct(75.0): {calc.is_correct(75.0)}")
    print(f"    is_correct(74.6): {calc.is_correct(74.6)}")
    print(f"    is_correct(74.4): {calc.is_correct(74.4)}")

    print("\n--- Round-trip from_json → to_dict ---\n")
    samples = [mc, tf, sa, fitb, match, calc]
    for obj in samples:
        d = obj.to_dict()
        restored = Question.from_json(d)
        match_type = type(restored).__name__ == type(obj).__name__
        print(f"  {type(obj).__name__}: round-trip ok={match_type}")


def main(argv: List[str] | None = None) -> int:
    p = argparse.ArgumentParser(description="Demo migrating question banks and using question objects")
    p.add_argument("--bank", help="Path to question bank JSON",
                   default="promptukit/data/question_banks/block-doku-sample.json")
    p.add_argument("--out", help="Write migrated JSON to PATH (optional)")
    p.add_argument("--inplace", action="store_true", help="Overwrite the source file (use with care)")
    p.add_argument("--preserve-raw", action="store_true",
                   help="When showing serialized objects, prefer original raw dict")
    p.add_argument("--new-types", action="store_true", default=True,
                   help="Show new question type samples (default: on)")
    args = p.parse_args(argv)

    bank_path = Path(args.bank)
    if not bank_path.exists():
        print(f"Bank not found: {bank_path}")
        return 2

    print(f"Loading: {bank_path}")
    data = load(bank_path)
    raw_questions = _flatten_data(data)
    if not raw_questions:
        print("No questions found in source.")
        return 1

    print("\nRaw first question keys:")
    first = raw_questions[0]
    print("  ", list(first.keys()))
    print("  inferred type:", infer_question_type(first))

    # Add question_type tags in-memory
    migrated = add_question_type_tags(data)
    migrated_questions = _flatten_data(migrated)
    print("\nAfter adding question_type (in-memory):")
    print("  first question_type:", migrated_questions[0].get("question_type"))

    # Optionally write migrated JSON to disk
    if args.out or args.inplace:
        destination = Path(args.out) if args.out else bank_path
        if destination.exists() and destination == bank_path and not args.inplace:
            print("Destination exists and --inplace not specified; not overwriting.")
        else:
            written = update_json_file(bank_path, destination)
            print(f"Wrote migrated JSON to: {written}")

    # Build objects from the in-memory migrated data
    objects = [Question.from_json(q) for q in migrated_questions]
    print(f"\nLoaded {len(objects)} question objects from bank:")
    for i, obj in enumerate(objects, 1):
        print(f" {i}) {obj.question_type}: {obj.text[:60]}")
        serialized = obj.to_dict(preserve_raw=args.preserve_raw)
        print("    serialized:", json.dumps(serialized, ensure_ascii=False)[:200])

    if args.new_types:
        _demo_new_types()

    print("\nDone. Use --out to write migrated JSON to disk, or --inplace to overwrite source.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
