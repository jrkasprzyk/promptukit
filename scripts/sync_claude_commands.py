#!/usr/bin/env python3
"""Mirror canonical promptukit/claude_commands/*.md → .claude/commands/*.md.

Canonical location is promptukit/claude_commands/ (shipped in the wheel).
.claude/commands/ holds copies so Claude Code reads them locally.

Usage:
    python scripts/sync_claude_commands.py [--check]

--check exits non-zero if any mirror is out of date (CI-friendly).
"""

from __future__ import annotations

import argparse
import filecmp
import shutil
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
SRC_DIR = REPO_ROOT / "promptukit" / "claude_commands"
DST_DIR = REPO_ROOT / ".claude" / "commands"


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument(
        "--check",
        action="store_true",
        help="Exit non-zero if mirrors are out of date; do not write.",
    )
    args = ap.parse_args()

    if not SRC_DIR.is_dir():
        print(f"missing canonical dir: {SRC_DIR}", file=sys.stderr)
        return 2

    DST_DIR.mkdir(parents=True, exist_ok=True)
    src_files = sorted(SRC_DIR.glob("*.md"))
    drift: list[str] = []

    for src in src_files:
        dst = DST_DIR / src.name
        if not dst.exists() or not filecmp.cmp(src, dst, shallow=False):
            drift.append(src.name)
            if not args.check:
                shutil.copyfile(src, dst)

    extras = [
        p.name
        for p in DST_DIR.glob("*.md")
        if not (SRC_DIR / p.name).exists()
    ]

    if args.check:
        if drift or extras:
            for name in drift:
                print(f"out of date: {name}")
            for name in extras:
                print(f"unexpected (not in canonical): {name}")
            return 1
        print("in sync")
        return 0

    for name in drift:
        print(f"updated {name}")
    if extras:
        print(
            "warning: .claude/commands/ has files not in canonical: "
            + ", ".join(extras),
            file=sys.stderr,
        )
    if not drift:
        print("already in sync")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
