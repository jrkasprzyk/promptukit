#!/usr/bin/env python3
"""Extract information from a trivia JSON file.

Usage examples:
  python scripts/extract_trivia.py --list-categories
  python scripts/extract_trivia.py --file assets/trivia.json --category music --fields prompt,answer
  python scripts/extract_trivia.py -i    # interactive picker

The script is permissive about JSON shape: it supports the project's
`{ "questions": [...] }` layout, a top-level mapping of categories -> list,
or a flat list of question objects that include a `category` field.
"""

from __future__ import annotations

import argparse
import json
import sys
import re
from collections import defaultdict
from pathlib import Path
from typing import Any, Dict, Iterable, List, Tuple

from .cli_helpers import load, pick, confirm


TRIVIA_PATH = Path(__file__).resolve().parent.parent / "assets" / "trivia.json"


def build_category_map(data: Any) -> Dict[str, List[dict]]:
    """Return a mapping category -> list[question]. Handles several shapes.

    Supported shapes:
    - { "questions": [ ... ] }
    - { "category1": [ ... ], "category2": [ ... ] }
    - [ { "category": "x", ... }, ... ]
    """
    cats: Dict[str, List[dict]] = defaultdict(list)

    if isinstance(data, dict):
        # Common project shape: { "questions": [ ... ], "categories": [...] }
        if "questions" in data and isinstance(data["questions"], list):
            for q in data["questions"]:
                cat = q.get("category") or "uncategorized"
                cats[cat].append(q)
            return dict(cats)

        # If top-level keys are lists, treat them as categories
        if all(isinstance(v, list) for v in data.values()):
            # ensure values are lists of dicts
            return {k: v for k, v in data.items()}

        # fallback: wrap the dict itself as a single item
        return {"data": [data]}

    if isinstance(data, list):
        for q in data:
            if isinstance(q, dict):
                cat = q.get("category") or "uncategorized"
                cats[cat].append(q)
            else:
                cats["data"].append({"value": q})
        return dict(cats)

    # anything else -> single bucket
    return {"data": [data]}


def list_categories(catmap: Dict[str, List[dict]]) -> List[Tuple[int, str, int]]:
    out: List[Tuple[int, str, int]] = []
    for i, (cat, items) in enumerate(sorted(catmap.items()), 1):
        out.append((i, cat, len(items)))
    return out


# `pick` is provided by `cli_helpers` (imports at top)


# `confirm` is provided by `cli_helpers` (imports at top)


def _pretty_answer(item: dict) -> str | None:
    """Return the human-readable answer text for a question item, if possible."""
    if not isinstance(item, dict):
        return None
    ans = item.get("answer")
    choices = item.get("choices") or []
    # integer index
    if isinstance(ans, int):
        if 0 <= ans < len(choices):
            return choices[ans]
        return str(ans)
    # numeric string
    if isinstance(ans, str) and ans.isdigit():
        idx = int(ans)
        if 0 <= idx < len(choices):
            return choices[idx]
        return ans
    # letter like 'A' or 'a'
    if isinstance(ans, str) and len(ans) == 1 and ans.isalpha():
        idx = ord(ans.upper()) - ord("A")
        if 0 <= idx < len(choices):
            return choices[idx]
        return ans
    # fallback
    return str(ans) if ans is not None else None


def print_item(item: dict, fields: Iterable[str] | None = None, json_lines: bool = False) -> None:
    if json_lines:
        print(json.dumps(item, ensure_ascii=False))
        return

    if not fields:
        print(json.dumps(item, indent=2, ensure_ascii=False))
        return

    # human-readable
    for f in fields:
        if f == "answer":
            pa = _pretty_answer(item)
            print(f"  answer: {pa}")
        elif f == "choices":
            chs = item.get("choices") or []
            print("  choices:")
            for i, ch in enumerate(chs):
                label = chr(ord("A") + i) if isinstance(i, int) else str(i)
                print(f"    {label}) {ch}")
        else:
            val = item.get(f, None)
            print(f"  {f}: {val}")
    print("  " + "-" * 60)


def parse_fields(arg: str | None) -> List[str] | None:
    if not arg:
        return None
    parts = [p.strip() for p in arg.split(",") if p.strip()]
    return parts or None


def order_fields(keys: Iterable[str]) -> List[str]:
    preferred = [
        "id",
        "category",
        "difficulty",
        "prompt",
        "choices",
        "answer",
        "quip_correct",
        "quip_wrong",
    ]
    kset = set(keys)
    ordered = [k for k in preferred if k in kset]
    extras = sorted(k for k in kset if k not in preferred)
    return ordered + extras


def parse_field_selection(sel: str, available: List[str]) -> List[str] | None:
    """Parse a user selection string into a list of field names.

    Accepts:
    - empty string -> None (meaning full item)
    - 'all' or '*' -> all available fields
    - numeric indices (space or comma separated) referencing `available` (0-based)
    - exact field names (case-insensitive)
    Returns None if the selection is invalid.
    """
    if not sel:
        return None
    toks = [t for t in re.split(r"[\s,]+", sel.strip()) if t]
    if not toks:
        return None
    if all(t.lower() in ("all", "*") for t in toks):
        return available

    # all digits -> indices
    if all(t.isdigit() for t in toks):
        idxs = [int(t) for t in toks]
        if any(i < 0 or i >= len(available) for i in idxs):
            return None
        return [available[i] for i in idxs]

    # otherwise try matching by name (case-insensitive)
    out: List[str] = []
    lower_map = {a.lower(): a for a in available}
    for t in toks:
        t_l = t.lower()
        if t_l in lower_map:
            out.append(lower_map[t_l])
        else:
            return None
    return out


def interactive_flow(path: Path, catmap: Dict[str, List[dict]]) -> int:
    data = load(path)
    schema_cats: List[str] = []
    if isinstance(data, dict):
        schema_cats = data.get("categories") or []

    # Combine schema categories (if present) with discovered categories.
    combined = []
    for c in (schema_cats or []):
        if c not in combined:
            combined.append(c)
    for c in sorted(catmap.keys()):
        if c not in combined:
            combined.append(c)

    if not combined:
        print("No categories found.")
        return 1

    while True:
        print("\nAvailable categories (schema first):")
        for i, c in enumerate(combined, 1):
            cnt = len(catmap.get(c, []))
            print(f"  {i}) {c} — {cnt}")

        cat = pick("Choose a category", combined)

        items = catmap.get(cat, [])
        if not items:
            print(f"  (no items found for category '{cat}')")
        else:
            # Collect available fields for this category and present a menu
            keys = set()
            for it in items:
                if isinstance(it, dict):
                    keys.update(it.keys())
            available_fields = order_fields(keys)

            if not available_fields:
                print("  (no fields available for items in this category)")
                fields = None
            else:
                # show numbered menu starting at 0
                print("\n  Fields:")
                for i, f in enumerate(available_fields):
                    print(f"    {i} {f}")

                # prompt until valid selection
                while True:
                    sel_raw = input("  Select fields (numbers space/comma-separated, 'all', or Enter for full items): ").strip()
                    sel = parse_field_selection(sel_raw, available_fields)
                    if sel is None and sel_raw:
                        print("    Invalid selection — try again.")
                        continue
                    fields = sel or None
                    break

            limit_raw = input("Limit results (Enter for no limit): ").strip()
            limit = int(limit_raw) if limit_raw.isdigit() else None

            to_print = items[:limit] if limit else items
            for item in to_print:
                print_item(item, fields)

        if not confirm("Extract again?"):
            break

    return 0


def main(argv: List[str] | None = None) -> int:
    argv = argv if argv is not None else sys.argv[1:]
    p = argparse.ArgumentParser(description="Extract info from a trivia JSON file")
    p.add_argument("--file", "-f", default=str(TRIVIA_PATH), help="Path to trivia JSON file")
    p.add_argument("--list-categories", action="store_true", help="List categories and counts")
    p.add_argument("--category", "-c", help="Category name (or index) to extract from")
    p.add_argument("--fields", "-F", help="Comma-separated fields to extract (e.g. prompt,answer)")
    p.add_argument("--list-fields", action="store_true", help="List available fields for a category")
    p.add_argument("--count", action="store_true", help="Show counts for selected category")
    p.add_argument("--limit", "-n", type=int, default=0, help="Limit number of items printed per category")
    p.add_argument("--json-lines", action="store_true", help="Output items as JSON Lines")
    p.add_argument("-i", "--interactive", action="store_true", help="Interactive mode")
    args = p.parse_args(argv)

    path = Path(args.file)
    if not path.exists():
        print(f"FATAL: file not found: {path}")
        return 2

    try:
        data = load(path)
    except json.JSONDecodeError as e:
        print(f"FATAL: invalid JSON — {e}")
        return 3

    catmap = build_category_map(data)

    if args.list_categories:
        # Show a single list of categories (schema order first if present),
        # and include available fields for each category to help selection.
        combined: List[str] = []
        if isinstance(data, dict) and data.get("categories"):
            for c in data.get("categories"):
                if c not in combined:
                    combined.append(c)
        for c in sorted(catmap.keys()):
            if c not in combined:
                combined.append(c)

        if not combined:
            print("No categories found.")
            return 0

        print("Categories (schema order if available):")
        for i, c in enumerate(combined, 1):
            items = catmap.get(c, [])
            count = len(items)
            # collect available fields for this category
            keys = set()
            for it in items:
                if isinstance(it, dict):
                    keys.update(it.keys())
            keys_list = sorted(keys) if keys else []
            fields_str = ", ".join(keys_list) if keys_list else "(no fields)"
            print(f"  {i}) {c} — {count} items; fields: {fields_str}")
        return 0

    if args.interactive or (not args.category and not args.fields and not args.list_fields and not args.count):
        return interactive_flow(path, catmap)

    # Resolve category: allow numeric index or name
    selected_cats: List[str]
    if args.category:
        cats_sorted = [c for c in sorted(catmap.keys())]
        if args.category.isdigit():
            idx = int(args.category)
            if 1 <= idx <= len(cats_sorted):
                selected_cats = [cats_sorted[idx - 1]]
            else:
                print(f"Category index out of range: {idx}")
                return 4
        else:
            # exact match or substring
            if args.category in catmap:
                selected_cats = [args.category]
            else:
                matches = [c for c in cats_sorted if args.category.lower() in c.lower()]
                if not matches:
                    print(f"No matching category for: {args.category}")
                    return 5
                if len(matches) > 1:
                    print("Multiple matches: choose one")
                    for i, m in enumerate(matches, 1):
                        print(f"  {i}) {m}")
                    choice = input("Pick number: ").strip()
                    if not choice.isdigit() or not (1 <= int(choice) <= len(matches)):
                        print("Invalid choice")
                        return 6
                    selected_cats = [matches[int(choice) - 1]]
                else:
                    selected_cats = matches
    else:
        selected_cats = list(sorted(catmap.keys()))

    fields = parse_fields(args.fields)

    # If the user asked to list available fields, show the union of keys
    # present in the selected categories and exit.
    if args.list_fields:
        for cat in selected_cats:
            items = catmap.get(cat, [])
            keys = set()
            for it in items:
                if isinstance(it, dict):
                    keys.update(it.keys())
            print(f"{cat}: {', '.join(sorted(keys))}")
        return 0

    for cat in selected_cats:
        items = catmap.get(cat, [])
        if args.count:
            print(f"{cat}: {len(items)}")
            continue

        print(f"\n=== Category: {cat} (items: {len(items)}) ===")
        to_print = items[: args.limit] if args.limit and args.limit > 0 else items
        for item in to_print:
            if fields is None:
                # default human-friendly summary: show id, prompt (if present), and the
                # human-readable answer (convert index -> choice text when possible).
                summary = []
                if isinstance(item, dict) and item.get("id"):
                    summary.append(f"id={item.get('id')}")
                if isinstance(item, dict) and item.get("prompt"):
                    summary.append(f"prompt={item.get('prompt')}")
                if isinstance(item, dict) and item.get("answer") is not None:
                    pa = _pretty_answer(item)
                    summary.append(f"answer={pa}")
                print("  - " + " | ".join(summary) if summary else json.dumps(item, ensure_ascii=False))
            else:
                print_item(item, fields, json_lines=args.json_lines)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
