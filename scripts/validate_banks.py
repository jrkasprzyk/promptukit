#!/usr/bin/env python3
"""Run promptukit question-bank validation across example banks.

Normalizes 'sections'/'categories' shapes into a top-level 'questions' list
before invoking the project's `validate_question.validate` function so we get
consistent error/warning output for all sample files.
"""

from pathlib import Path
import json
import sys

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from promptukit.questions import validate_question


def normalize(path: Path):
    try:
        data = json.load(path.open(encoding="utf-8"))
    except Exception as e:
        return None, f"Failed to load JSON: {e}"

    # If already a flat object with 'questions', use as-is.
    if isinstance(data, dict) and isinstance(data.get("questions"), list):
        return data, None

    # If shape uses 'rounds', 'sections', or 'categories' (sectioned formats),
    # flatten into top-level questions preserving common keys when present.
    if isinstance(data, dict) and ("rounds" in data or "sections" in data or "categories" in data):
        if "rounds" in data:
            key = "rounds"
        elif "sections" in data:
            key = "sections"
        else:
            key = "categories"
        sections_raw = data.get(key, [])
        out = []
        for sec in sections_raw:
            if isinstance(sec, dict):
                qitems = sec.get("questions") or sec.get("items") or []
            else:
                qitems = []
            for it in qitems:
                if isinstance(it, str):
                    q = {"prompt": it, "choices": []}
                else:
                    q = {
                        "prompt": it.get("prompt") or it.get("q") or it.get("question") or it.get("text") or "",
                        "choices": it.get("choices") or it.get("answers") or [],
                    }
                    if it.get("category"):
                        q["category"] = it.get("category")
                    if it.get("id"):
                        q["id"] = it.get("id")
                    if it.get("difficulty"):
                        q["difficulty"] = it.get("difficulty")
                    if it.get("answer") is not None:
                        q["answer"] = it.get("answer")
                    if it.get("quip_correct"):
                        q["quip_correct"] = it.get("quip_correct")
                    if it.get("quip_wrong"):
                        q["quip_wrong"] = it.get("quip_wrong")
                out.append(q)
        return {"questions": out}, None

    # If file is a bare list, treat as questions list
    if isinstance(data, list):
        return {"questions": data}, None

    return {"questions": []}, None


def main():
    base = Path("promptukit/data/question_banks")
    # Dynamically discover all JSON files under the question_banks directory.
    if not base.exists():
        print(f"  SKIP: directory not found: {base}")
        return 2
    structural_skip = {"question_schema.json", "pub-quiz-sample.json"}
    files = sorted([
        p for p in base.rglob("*.json")
        if p.is_file() and p.name not in structural_skip
    ])

    overall_ok = True
    for p in files:
        print("\n" + "=" * 78)
        print(f"Validating: {p}")
        if not p.exists():
            print(f"  SKIP: file not found: {p}")
            # Don't treat missing example files as a failing condition; they
            # were intentionally removed in some workflows. Skip silently
            # without flipping `overall_ok` so the script focuses on real
            # validation errors in present files.
            continue
        data, err = normalize(p)
        if err:
            print(f"  ERROR: {err}")
            overall_ok = False
            continue
        errors, warnings = validate_question.validate(data)
        print(f"  Errors: {len(errors)}  Warnings: {len(warnings)}")
        if errors:
            for e in errors[:50]:
                print("   ERROR:", e)
            if len(errors) > 50:
                print(f"   ... and {len(errors)-50} more errors")
            overall_ok = False
        if warnings:
            for w in warnings[:50]:
                print("   WARN:", w)
        try:
            validate_question.print_stats(data)
        except Exception as e:
            print("  (print_stats failed):", e)

    return 0 if overall_ok else 2


if __name__ == '__main__':
    sys.exit(main())
