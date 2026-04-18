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
        load_resource('question_banks/example_sections.json')
        load_resource('example_sections.json')  # will try data/question_banks
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
