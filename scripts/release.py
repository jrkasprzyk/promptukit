#!/usr/bin/env python3
"""Bump version, update CHANGELOG, commit, push, and tag a release.

Usage:
    python scripts/release.py 0.1.2

Cross-platform (Git Bash, PowerShell, cmd). You still need to publish the
GitHub Release manually to trigger the PyPI upload workflow.

Assumes CHANGELOG.md follows the Keep a Changelog format with:
  - a `## [Unreleased]` heading whose content is moved to the new section
  - a `[Unreleased]: <url>/compare/vPREV...HEAD` link reference at the bottom
"""
from __future__ import annotations

import re
import subprocess
import sys
from datetime import date
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
PYPROJECT = REPO_ROOT / "pyproject.toml"
CHANGELOG = REPO_ROOT / "CHANGELOG.md"


def run(*args: str, capture: bool = False) -> str:
    result = subprocess.run(args, cwd=REPO_ROOT, capture_output=capture, text=True)
    if result.returncode != 0:
        sys.exit(result.returncode)
    return result.stdout.strip() if capture else ""


def bump_pyproject(new_version: str) -> str:
    text = PYPROJECT.read_text(encoding="utf-8")
    current = re.search(r'(?m)^version\s*=\s*"([^"]+)"', text)
    if not current:
        sys.exit(f"error: no version line in {PYPROJECT}")
    updated, n = re.subn(
        r'(?m)^(version\s*=\s*")[^"]+(")',
        rf'\g<1>{new_version}\g<2>',
        text,
        count=1,
    )
    if n != 1:
        sys.exit(f"error: could not update version line in {PYPROJECT}")
    PYPROJECT.write_text(updated, encoding="utf-8")
    return current.group(1)


def bump_changelog(new_version: str) -> None:
    if not CHANGELOG.exists():
        sys.exit(f"error: {CHANGELOG} not found")
    text = CHANGELOG.read_text(encoding="utf-8")

    unreleased_re = re.compile(r'^## \[Unreleased\]\s*$', re.MULTILINE)
    m = unreleased_re.search(text)
    if not m:
        sys.exit(
            f"error: no '## [Unreleased]' heading in {CHANGELOG}. "
            "Add one and move in-progress entries under it."
        )

    rest = text[m.end():]
    next_heading = re.search(r'^## \[', rest, re.MULTILINE)
    link_refs = re.search(r'^\[Unreleased\]:', rest, re.MULTILINE)
    candidates = [x.start() for x in (next_heading, link_refs) if x is not None]
    if not candidates:
        sys.exit(f"error: {CHANGELOG} has no later section or link refs after [Unreleased]")
    content_end = m.end() + min(candidates)
    unreleased_content = text[m.end():content_end]

    if not unreleased_content.strip():
        print("warning: [Unreleased] is empty — release will have no changelog entries.", file=sys.stderr)
        reply = input("continue anyway? [y/N] ").strip().lower()
        if reply not in ("y", "yes"):
            sys.exit(1)

    today = date.today().isoformat()
    content = unreleased_content.strip()
    body = f"\n\n{content}" if content else ""
    new_section = f"## [Unreleased]\n\n## [{new_version}] — {today}{body}\n\n"
    text = text[: m.start()] + new_section + text[content_end:]

    unreleased_link_re = re.compile(
        r'^\[Unreleased\]:\s*(\S+)/compare/v(\S+?)\.\.\.HEAD\s*$',
        re.MULTILINE,
    )
    lm = unreleased_link_re.search(text)
    if not lm:
        sys.exit(f"error: no '[Unreleased]: <url>/compare/vPREV...HEAD' link ref in {CHANGELOG}")
    base = lm.group(1)
    prev = lm.group(2)
    new_lines = (
        f"[Unreleased]: {base}/compare/v{new_version}...HEAD\n"
        f"[{new_version}]: {base}/compare/v{prev}...v{new_version}"
    )
    text = text[: lm.start()] + new_lines + text[lm.end():]

    CHANGELOG.write_text(text, encoding="utf-8")


def derive_repo_slug() -> str | None:
    try:
        remote = run("git", "config", "--get", "remote.origin.url", capture=True)
    except SystemExit:
        return None
    m = re.search(r"github\.com[:/](.+?)(?:\.git)?$", remote)
    return m.group(1) if m else None


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

    current = bump_pyproject(new_version)
    print(f"bumping {current} -> {new_version}")
    bump_changelog(new_version)

    run("git", "add", "pyproject.toml", "CHANGELOG.md")
    run("git", "commit", "-m", f"Release {new_version}")
    run("git", "push")
    run("git", "tag", tag)
    run("git", "push", "origin", tag)

    print(f"\nDone. Tag {tag} is pushed.")
    print("\nNext step — publish the GitHub Release to trigger the PyPI upload:")
    slug = derive_repo_slug()
    if slug:
        print(f"  https://github.com/{slug}/releases/new?tag={tag}")
    else:
        print(f"  <your repo>/releases/new?tag={tag}")


if __name__ == "__main__":
    main()
