#!/usr/bin/env python3
"""Manage question bank JSON files: create, copy, or extract subsets.

Usage examples:
  python -m promptukit.questions.question_bank create --dest content/question_banks/new.json --categories music,film-and-tv
  python -m promptukit.questions.question_bank copy --src content/question_banks/block-doku-questions.json --dest content/question_banks/backup.json
  python -m promptukit.questions.question_bank extract --src content/question_banks/block-doku-questions.json --dest content/question_banks/music_subset.json --categories music --difficulty easy
  python -m promptukit.questions.question_bank extract -i --src content/question_banks/block-doku-questions.json --dest content/question_banks/pick.json
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Any, List, Optional

from promptukit.utils.cli_helpers import load, save, pick, confirm


def _load_questions(data: Any) -> List[dict]:
    """Return a flat list of question dicts from several supported JSON shapes.

    The project uses either a top-level `questions` list or a mapping of
    category -> list. This helper normalizes those shapes into a single
    list of question objects for downstream filtering.
    """
    if isinstance(data, dict):
        if "questions" in data and isinstance(data["questions"], list):
            return [q for q in data["questions"] if isinstance(q, dict)]
        # top-level category -> list mapping
        if all(isinstance(v, list) for v in data.values()):
            out: List[dict] = []
            for v in data.values():
                if isinstance(v, list):
                    out.extend([q for q in v if isinstance(q, dict)])
            return out
        # fallback: dict itself as single item
        return [data] if isinstance(data, dict) else []
    if isinstance(data, list):
        return [q for q in data if isinstance(q, dict)]
    return []


def _categories_of(questions: List[dict]) -> List[str]:
    cats: List[str] = []
    for q in questions:
        c = q.get("category")
        if c and c not in cats:
            cats.append(c)
    return cats


def _parse_csv(s: Optional[str]) -> List[str]:
    if not s:
        return []
    return [p.strip() for p in s.split(",") if p.strip()]


def filter_questions(questions: List[dict], categories: Optional[List[str]] = None, ids: Optional[List[str]] = None,
                     difficulty: Optional[str] = None, match: Optional[str] = None) -> List[dict]:
    categories = categories or []
    ids = ids or []
    rx = re.compile(match, re.IGNORECASE) if match else None

    def keep(q: dict) -> bool:
        if categories:
            qcat = (q.get("category") or "").lower()
            # accept substring match or exact
            if not any(c.lower() == qcat or c.lower() in qcat for c in categories):
                return False
        if ids:
            if q.get("id") not in ids:
                return False
        if difficulty:
            if (q.get("difficulty") or "").lower() != difficulty.lower():
                return False
        if rx:
            txt = (q.get("prompt") or "") + " " + " ".join(str(x) for x in q.get("choices", []))
            if not rx.search(txt):
                return False
        return True

    return [q for q in questions if keep(q)]


def ensure_dest(path: Path, force: bool = False) -> bool:
    """Return True if it's OK to write `path`. Prompt unless `force`."""
    if not path.exists():
        parent = path.parent
        if not parent.exists():
            parent.mkdir(parents=True, exist_ok=True)
        return True
    if force:
        return True
    return confirm(f"Destination {path} exists — overwrite?")


def cmd_create(args: argparse.Namespace) -> int:
    dest = Path(args.dest)
    cats = _parse_csv(args.categories)
    data = {"categories": cats, "questions": []}
    if not ensure_dest(dest, force=args.force):
        print("Aborted.")
        return 2
    save(dest, data)
    print(f"Created: {dest} ({len(cats)} categories, 0 questions)")
    return 0


def cmd_copy(args: argparse.Namespace) -> int:
    src = Path(args.src)
    dest = Path(args.dest)
    if not src.exists():
        print(f"Source not found: {src}")
        return 3
    data = load(src)
    if not ensure_dest(dest, force=args.force):
        print("Aborted.")
        return 4
    save(dest, data)
    print(f"Copied: {src} -> {dest}")
    return 0


def cmd_extract(args: argparse.Namespace) -> int:
    src = Path(args.src)
    dest = Path(args.dest)
    if not src.exists():
        print(f"Source not found: {src}")
        return 3
    data = load(src)
    questions = _load_questions(data)
    # interactive selection of categories if requested
    cats = _parse_csv(args.categories) if args.categories else []
    if args.interactive:
        available = _categories_of(questions)
        if not available:
            print("No categories found in source.")
            return 5
        cat = pick("Choose a category to extract (or type a name)", available)
        cats = [cat]
    ids = _parse_csv(args.ids) if args.ids else []
    filtered = filter_questions(questions, categories=cats, ids=ids, difficulty=args.difficulty, match=args.match)
    if args.limit and args.limit > 0:
        filtered = filtered[: args.limit]
    out_data = {"categories": _categories_of(filtered), "questions": filtered}
    if not ensure_dest(dest, force=args.force):
        print("Aborted.")
        return 6
    save(dest, out_data)
    print(f"Wrote {len(filtered)} question(s) to {dest}")
    return 0


def main(argv: List[str] | None = None) -> int:
    argv = argv if argv is not None else sys.argv[1:]
    p = argparse.ArgumentParser(description="Create, copy, or extract question bank JSON files")
    sp = p.add_subparsers(dest="cmd", required=True)

    p_create = sp.add_parser("create", help="Create a new question bank JSON file (template)")
    p_create.add_argument("--dest", required=True, help="Destination path for new JSON")
    p_create.add_argument("--categories", help="Comma-separated initial categories")
    p_create.add_argument("-f", "--force", action="store_true", help="Overwrite destination if exists")
    p_create.set_defaults(func=cmd_create)

    p_copy = sp.add_parser("copy", help="Copy an existing question bank JSON file to a new path")
    p_copy.add_argument("--src", required=True, help="Source question bank JSON")
    p_copy.add_argument("--dest", required=True, help="Destination path")
    p_copy.add_argument("-f", "--force", action="store_true", help="Overwrite destination if exists")
    p_copy.set_defaults(func=cmd_copy)

    p_extract = sp.add_parser("extract", help="Extract a subset of questions into a new file")
    p_extract.add_argument("--src", required=True, help="Source question bank JSON")
    p_extract.add_argument("--dest", required=True, help="Destination JSON file to write")
    p_extract.add_argument("--categories", help="Comma-separated category names (substring matches allowed)")
    p_extract.add_argument("--ids", help="Comma-separated question ids to include (exact match)")
    p_extract.add_argument("--difficulty", help="Filter by difficulty (easy|medium|hard)")
    p_extract.add_argument("--match", help="Regex to match against prompt+choices")
    p_extract.add_argument("--limit", type=int, default=0, help="Limit number of questions written")
    p_extract.add_argument("-i", "--interactive", action="store_true", help="Interactive category picker")
    p_extract.add_argument("-f", "--force", action="store_true", help="Overwrite destination if exists")
    p_extract.set_defaults(func=cmd_extract)

    args = p.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
