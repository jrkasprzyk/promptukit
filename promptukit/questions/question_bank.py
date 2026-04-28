#!/usr/bin/env python3
"""Manage question bank JSON files: create, copy, or extract subsets.

Usage examples:
    python -m promptukit.questions.question_bank create --dest promptukit/data/question_banks/new.json --categories music,film-and-tv
    python -m promptukit.questions.question_bank copy --src promptukit/data/question_banks/block-doku-sample.json --dest promptukit/data/question_banks/backup.json
    python -m promptukit.questions.question_bank extract --src promptukit/data/question_banks/block-doku-sample.json --dest promptukit/data/question_banks/music_subset.json --categories music --difficulty easy
    python -m promptukit.questions.question_bank extract -i --src promptukit/data/question_banks/block-doku-sample.json --dest promptukit/data/question_banks/pick.json
    python -m promptukit.questions.question_bank extract --src promptukit/data/question_banks/block-doku-sample.json --dest promptukit/data/question_banks/exam_subset.json --numbers 5,10,15-18
    python -m promptukit.questions.question_bank extract -I --src promptukit/data/question_banks/block-doku-sample.json --dest promptukit/data/question_banks/pick.json
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Any, List, Optional

from promptukit.utils.cli_helpers import load, save, pick, confirm, pick_questions
from promptukit.utils.json_tools import update_json_file, flatten_questions
from promptukit.questions import text_audit



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


def _parse_numbers(s: str) -> List[int]:
    """Parse a number/range string like '5,10,15-18' into a sorted list of 1-based indices."""
    result: set[int] = set()
    for token in s.split(","):
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
    return sorted(result)


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

def _setup_template(kind: str) -> dict:
    if kind == "pub_quiz":
        from promptukit.exams.create_pub_quiz import DEFAULT_METADATA
    else:
        from promptukit.exams.create_exam import DEFAULT_METADATA
    return dict(DEFAULT_METADATA)


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
    questions = flatten_questions(data)

    # --numbers: pick by 1-based position before any other filter
    if args.numbers:
        indices = _parse_numbers(args.numbers)
        questions = [questions[i - 1] for i in indices if 1 <= i <= len(questions)]

    # -i: interactive single-category filter
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

    # -I: interactive multi-select from the (already-filtered) question list
    if args.interactive_questions:
        if not filtered:
            print("No questions to select from.")
            return 7
        chosen = pick_questions(filtered)
        if not chosen:
            print("No questions selected. Aborted.")
            return 8
        filtered = [filtered[i] for i in chosen]

    out_data = {"categories": _categories_of(filtered), "questions": filtered}
    if not ensure_dest(dest, force=args.force):
        print("Aborted.")
        return 6
    save(dest, out_data)
    print(f"Wrote {len(filtered)} question(s) to {dest}")

    if args.setup_dest:
        setup_dest = Path(args.setup_dest)
        if not ensure_dest(setup_dest, force=args.force):
            print("Question subset was written, but setup artifact was not written.")
            return 9
        save(setup_dest, _setup_template(args.artifact_kind))
        print(f"Wrote {args.artifact_kind.replace('_', ' ')} setup artifact to {setup_dest}")

    return 0


def cmd_migrate(args: argparse.Namespace) -> int:
    """Add ``question_type`` tags to a JSON file (write in-place or to dest)."""
    src = Path(args.src)
    dest = Path(args.dest) if args.dest else None
    if not src.exists():
        print(f"Source not found: {src}")
        return 3
    if dest and dest.exists() and not args.force:
        if not confirm(f"Destination {dest} exists — overwrite?"):
            print("Aborted.")
            return 4
    out = update_json_file(src, dest)
    print(f"Updated: {src} -> {out}")
    return 0


def _print_text_issues(issues: list[text_audit.TextIssue]) -> None:
    for issue in issues:
        print("  " + issue.format())


def cmd_audit_text(args: argparse.Namespace) -> int:
    """Audit JSON bank text for encoding and Unicode hazards."""
    src = Path(args.src)
    issues = text_audit.audit_path(src, ascii_only=args.ascii_only)
    if issues:
        print(f"Text audit found {len(issues)} issue(s):")
        _print_text_issues(issues)
        return 1
    print(f"Text audit passed: {src}")
    return 0


def _fix_one_text_file(src: Path, dest: Path, *, force: bool, ascii_only: bool) -> tuple[int, bool]:
    if dest.exists() and dest != src and not force:
        if not confirm(f"Destination {dest} exists - overwrite?"):
            print(f"Skipped: {src}")
            return 2, False
    try:
        changed = text_audit.fix_file(src, dest, ascii_only=ascii_only)
    except (UnicodeDecodeError, json.JSONDecodeError) as e:
        print(f"FATAL: cannot fix {src}: {e}")
        return 1, False

    remaining = text_audit.audit_file(dest, ascii_only=ascii_only)
    if remaining:
        print(f"Remaining issue(s) after fixing {dest}:")
        _print_text_issues(remaining)
        return 1, changed
    status = "rewrote" if changed else "already clean"
    print(f"{status}: {src} -> {dest}")
    return 0, changed


def cmd_fix_text(args: argparse.Namespace) -> int:
    """Apply safe deterministic text repairs to JSON bank files."""
    src = Path(args.src)
    dest_arg = Path(args.dest) if args.dest else None

    if not src.exists():
        print(f"Source not found: {src}")
        return 3
    if not args.in_place and dest_arg is None:
        print("Pass --dest to write a repaired copy, or --in-place to overwrite the source.")
        return 2

    paths = text_audit.iter_json_paths(src)
    if not paths:
        print(f"No JSON files found: {src}")
        return 3

    overall = 0
    changed_count = 0
    for path in paths:
        if args.in_place:
            dest = path
        elif src.is_dir():
            assert dest_arg is not None
            dest = dest_arg / path.relative_to(src)
        else:
            assert dest_arg is not None
            dest = dest_arg
        rc, changed = _fix_one_text_file(path, dest, force=args.force, ascii_only=args.ascii_only)
        changed_count += int(changed)
        if rc:
            overall = rc

    if overall == 0:
        print(f"Text fix complete: {changed_count}/{len(paths)} file(s) changed.")
    return overall


def cmd_render_audit(args: argparse.Namespace) -> int:
    """Check that bank text survives supported render targets."""
    src = Path(args.src)
    issues = text_audit.audit_render_path(src, target=args.target, encoding=args.encoding)
    if issues:
        print(f"Render audit found {len(issues)} issue(s):")
        _print_text_issues(issues)
        return 1
    target = args.target if args.target != "all" else "pdf/html/cli"
    print(f"Render audit passed ({target}): {src}")
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

    p_migrate = sp.add_parser("migrate", help="Add question_type tags to a JSON file (migrate schema)")
    p_migrate.add_argument("--src", required=True, help="Source question bank JSON")
    p_migrate.add_argument("--dest", help="Destination path (optional). If omitted, overwrites source")
    p_migrate.add_argument("-f", "--force", action="store_true", help="Overwrite destination if exists")
    p_migrate.set_defaults(func=cmd_migrate)

    p_audit_text = sp.add_parser("audit-text", help="Audit JSON text for Unicode/encoding hazards")
    p_audit_text.add_argument("--src", required=True, help="Question bank JSON file or directory")
    p_audit_text.add_argument(
        "--ascii-only",
        action="store_true",
        help="Also flag all non-ASCII characters for strict downstream tools",
    )
    p_audit_text.set_defaults(func=cmd_audit_text)

    p_fix_text = sp.add_parser("fix-text", help="Repair safe Unicode/encoding hazards in bank text")
    p_fix_text.add_argument("--src", required=True, help="Question bank JSON file or directory")
    p_fix_text.add_argument("--dest", help="Destination JSON file or directory for repaired output")
    p_fix_text.add_argument("--in-place", action="store_true", help="Overwrite source file(s)")
    p_fix_text.add_argument(
        "--ascii-only",
        action="store_true",
        help="Fold text to ASCII where possible after other repairs",
    )
    p_fix_text.add_argument("-f", "--force", action="store_true", help="Overwrite destination if exists")
    p_fix_text.set_defaults(func=cmd_fix_text)

    p_render_audit = sp.add_parser("render-audit", help="Check bank text against PDF/HTML/CLI render targets")
    p_render_audit.add_argument("--src", required=True, help="Question bank JSON file or directory")
    p_render_audit.add_argument("--target", choices=["all", "pdf", "html", "cli"], default="all")
    p_render_audit.add_argument(
        "--encoding",
        default="utf-8",
        help="Encoding to test for --target cli (default: utf-8)",
    )
    p_render_audit.set_defaults(func=cmd_render_audit)

    p_extract = sp.add_parser("extract", help="Extract a subset of questions into a new file")
    p_extract.add_argument("--src", required=True, help="Source question bank JSON")
    p_extract.add_argument("--dest", required=True, help="Destination JSON file to write")
    p_extract.add_argument("--categories", help="Comma-separated category names (substring matches allowed)")
    p_extract.add_argument("--ids", help="Comma-separated question ids to include (exact match)")
    p_extract.add_argument("--difficulty", help="Filter by difficulty (easy|medium|hard)")
    p_extract.add_argument("--match", help="Regex to match against prompt+choices")
    p_extract.add_argument("--numbers", help="1-based question numbers or ranges to include (e.g. 5,10,15-18)")
    p_extract.add_argument("--limit", type=int, default=0, help="Limit number of questions written")
    p_extract.add_argument("-i", "--interactive", action="store_true", help="Interactive category picker")
    p_extract.add_argument("-I", "--interactive-questions", action="store_true",
                           help="Interactive multi-select: browse and toggle individual questions")
    p_extract.add_argument("--setup-dest",
                           help="Optional destination for a matching exam/pub-quiz setup JSON template")
    p_extract.add_argument("--artifact-kind", choices=["exam", "pub_quiz"], default="exam",
                           help="Setup template type to write with --setup-dest")
    p_extract.add_argument("-f", "--force", action="store_true", help="Overwrite destination if exists")
    p_extract.set_defaults(func=cmd_extract)

    args = p.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
