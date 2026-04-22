#!/usr/bin/env python3
"""Demo: migrate question banks and use the Question classes.

This script demonstrates:
- Inferring and adding `question_type` tags to legacy JSON
- Loading questions as `Question`/`MultipleChoice` objects
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
from promptukit.questions.question_models import Question


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


def _summarize(obj: Question) -> Dict[str, Any]:
    s: Dict[str, Any] = {"type": obj.question_type, "text": getattr(obj, "text", None)}
    if hasattr(obj, "choices"):
        s["choices"] = getattr(obj, "choices")
    if hasattr(obj, "answer_index"):
        s["answer_index"] = getattr(obj, "answer_index")
    if hasattr(obj, "answer_text"):
        s["answer_text"] = getattr(obj, "answer_text")
    return s


def main(argv: List[str] | None = None) -> int:
    p = argparse.ArgumentParser(description="Demo migrating question banks and using question objects")
    p.add_argument("--bank", help="Path to question bank JSON",
                   default="promptukit/data/question_banks/block-doku-sample.json")
    p.add_argument("--out", help="Write migrated JSON to PATH (optional)")
    p.add_argument("--inplace", action="store_true", help="Overwrite the source file (use with care)")
    p.add_argument("--preserve-raw", action="store_true",
                   help="When showing serialized objects, prefer original raw dict")
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
    items = migrated_questions
    objects = [Question.from_json(q) for q in items]
    print(f"\nLoaded {len(objects)} question objects:")
    for i, obj in enumerate(objects, 1):
        summary = _summarize(obj)
        print(f" {i}) {summary['type']}: {summary['text']}")
        if "choices" in summary:
            print("    choices:", summary["choices"])
        print("    answer_index:", summary.get("answer_index"), "answer_text:", summary.get("answer_text"))
        serialized = obj.to_dict(preserve_raw=args.preserve_raw)
        print("    serialized (sample):", json.dumps(serialized, ensure_ascii=False)[:200])

    print("\nDone. Use --out to write migrated JSON to disk, or --inplace to overwrite source.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
