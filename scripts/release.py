#!/usr/bin/env python3
"""Bump version, commit, push, and tag a release.

Usage:
    python scripts/release.py 0.1.2

Equivalent to scripts/release.sh but works on Windows (PowerShell/cmd).
You still need to publish the GitHub Release manually to trigger PyPI upload.
"""
from __future__ import annotations

import re
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
PYPROJECT = REPO_ROOT / "pyproject.toml"


def run(*args: str, capture: bool = False) -> str:
    result = subprocess.run(args, cwd=REPO_ROOT, capture_output=capture, text=True)
    if result.returncode != 0:
        sys.exit(result.returncode)
    return result.stdout.strip() if capture else ""


def main() -> None:
    if len(sys.argv) != 2:
        print(f"Usage: python {sys.argv[0]} <new-version>   (e.g. 0.1.2)", file=sys.stderr)
        sys.exit(1)

    new_version = sys.argv[1]
    tag = f"v{new_version}"

    if not re.match(r"^\d+\.\d+\.\d+([a-z0-9.+-]*)?$", new_version):
        print(f"error: '{new_version}' doesn't look like a semver string (e.g. 0.1.2)", file=sys.stderr)
        sys.exit(1)

    dirty = subprocess.run(
        ["git", "status", "--porcelain"], cwd=REPO_ROOT, capture_output=True, text=True
    ).stdout.strip()
    if dirty:
        print("error: working tree is dirty. commit or stash changes first.", file=sys.stderr)
        print(dirty, file=sys.stderr)
        sys.exit(1)

    branch = run("git", "rev-parse", "--abbrev-ref", "HEAD", capture=True)
    if branch != "main":
        print(f"warning: you are on branch '{branch}', not 'main'.", file=sys.stderr)
        reply = input("continue anyway? [y/N] ").strip().lower()
        if reply not in ("y", "yes"):
            sys.exit(1)

    tag_exists = subprocess.run(
        ["git", "rev-parse", tag], cwd=REPO_ROOT, capture_output=True
    ).returncode == 0
    if tag_exists:
        print(f"error: tag '{tag}' already exists.", file=sys.stderr)
        sys.exit(1)

    text = PYPROJECT.read_text(encoding="utf-8")
    updated, n = re.subn(
        r'(?m)^(version\s*=\s*")[^"]+(")',
        rf'\g<1>{new_version}\g<2>',
        text,
        count=1,
    )
    if n != 1:
        print(f"error: could not find a version line to update in {PYPROJECT}", file=sys.stderr)
        sys.exit(1)

    current = re.search(r'(?m)^version\s*=\s*"([^"]+)"', text)
    print(f"bumping {current.group(1) if current else '?'} -> {new_version}")

    PYPROJECT.write_text(updated, encoding="utf-8")

    run("git", "add", "pyproject.toml")
    run("git", "commit", "-m", f"bump version to {new_version}")
    run("git", "push")
    run("git", "tag", tag)
    run("git", "push", "origin", tag)

    print(f"\nDone. Tag {tag} is pushed.")
    print(f"\nNext step — publish the GitHub Release to trigger the PyPI upload:")
    print(f"  https://github.com/jrkasprzyk/promptukit/releases/new?tag={tag}")


if __name__ == "__main__":
    main()
