"""Shared CLI helpers used by the trivia scripts.

Keep these functions minimal and import-friendly whether the scripts
are executed directly or as a package.
"""
from __future__ import annotations

import json
from importlib import resources
from pathlib import Path
from typing import Any, List


def load(path: Path) -> Any:
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def save(path: Path, data: Any) -> None:
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
        f.write("\n")


def load_resource(relpath: str) -> Any:
    """Load a JSON resource bundled with the package under `promptukit/data`.

    Examples:
        load_resource('question_banks/crb-water-management-sample.json')
        load_resource('crb-water-management-sample.json')  # will try data/question_banks
    """
    base = resources.files('promptukit').joinpath('data')
    target = base.joinpath(relpath)
    try:
        if target.is_file():
            with target.open('r', encoding='utf-8') as fh:
                return json.load(fh)
    except Exception:
        # Some environments may not support .is_file(); fall through to alternative checks
        pass

    # If a bare filename was provided, try the common subdirectory 'question_banks'
    if '/' not in relpath and '\\' not in relpath:
        alt = base.joinpath('question_banks').joinpath(relpath)
        if alt.is_file():
            with alt.open('r', encoding='utf-8') as fh:
                return json.load(fh)

    raise FileNotFoundError(f"Packaged resource not found: {relpath!r}")


def pick(label: str, options: List[str]) -> str:
    """Show a numbered menu and return the chosen option.

    Accepts a numeric choice, an exact name, a case-insensitive match,
    or a unique substring (if that disambiguates).
    """
    print(f"\n  {label}")
    for i, opt in enumerate(options, 1):
        print(f"    {i}) {opt}")
    while True:
        raw = input("  Choice: ").strip()
        if raw.isdigit() and 1 <= int(raw) <= len(options):
            return options[int(raw) - 1]

        if raw:
            # exact match
            if raw in options:
                return raw
            # case-insensitive exact
            lr = raw.lower()
            for opt in options:
                if opt.lower() == lr:
                    return opt
            # unique substring match
            matches = [opt for opt in options if lr in opt.lower()]
            if len(matches) == 1:
                return matches[0]

        print(f"    Please enter a number between 1 and {len(options)}, or an exact name.")


def confirm(msg: str) -> bool:
    while True:
        raw = input(f"  {msg} [y/n]: ").strip().lower()
        if raw in ("y", "yes"):
            return True
        if raw in ("n", "no"):
            return False


def pick_questions(questions: List[Any]) -> List[int]:
    """Interactive multi-select: show numbered questions, return chosen 0-based indices.

    The user types numbers or ranges (e.g. "5,10,15-18") to toggle selections,
    "done" or blank to confirm, "all" to select all, "clear" to deselect all,
    "list" to reprint the menu.
    """
    selected: set[int] = set()

    def _render() -> None:
        print()
        for i, q in enumerate(questions, 1):
            marker = "[x]" if (i - 1) in selected else "[ ]"
            prompt_text = (q.get("prompt") or q.get("q") or q.get("question") or "")[:72]
            cat = q.get("category", "")
            suffix = f"  ({cat})" if cat else ""
            print(f"  {marker} {i:>4}.  {prompt_text}{suffix}")
        total = len(selected)
        print(f"\n  {total} selected. Commands: numbers/ranges to toggle (e.g. 5,10,15-18), "
              "'all', 'clear', 'list', or blank/done to confirm.")

    def _parse_tokens(raw: str) -> set[int]:
        result: set[int] = set()
        for token in raw.split(","):
            token = token.strip()
            if "-" in token:
                parts = token.split("-", 1)
                try:
                    lo, hi = int(parts[0]), int(parts[1])
                    result.update(range(lo, hi + 1))
                except ValueError:
                    pass
            elif token.isdigit():
                result.add(int(token))
        return result

    _render()
    while True:
        raw = input("  > ").strip().lower()
        if raw in ("", "done"):
            break
        if raw == "all":
            selected = set(range(len(questions)))
            print(f"  All {len(selected)} selected.")
            continue
        if raw == "clear":
            selected.clear()
            print("  Selection cleared.")
            continue
        if raw == "list":
            _render()
            continue
        indices = _parse_tokens(raw)
        valid = {i - 1 for i in indices if 1 <= i <= len(questions)}
        if not valid:
            print(f"  No valid numbers found. Enter numbers 1-{len(questions)}.")
            continue
        # toggle: add unselected, remove already-selected
        to_add = valid - selected
        to_remove = valid & selected
        selected ^= valid
        if to_add and to_remove:
            print(f"  Added {sorted(i+1 for i in to_add)}, removed {sorted(i+1 for i in to_remove)}.")
        elif to_add:
            print(f"  Added {sorted(i+1 for i in to_add)}. Total: {len(selected)}")
        else:
            print(f"  Removed {sorted(i+1 for i in to_remove)}. Total: {len(selected)}")

    return sorted(selected)
