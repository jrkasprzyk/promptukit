"""Bundled Claude Code slash-command prompts for promptukit workflows.

Public API:
    list_commands()              -> list[str]
    get_command(name)            -> str
    get_command_path(name)       -> pathlib.Path
    install(dest=None, force=False, names=None) -> list[pathlib.Path]

CLI:
    promptukit-claude-commands list
    promptukit-claude-commands show <name>
    promptukit-claude-commands install [--dest DIR] [--force] [name ...]

`install` defaults to writing into `./.claude/commands/` under the current
working directory (project-local). Pass `--dest` to override (e.g.
`~/.claude/commands` for user-global).
"""

from __future__ import annotations

import argparse
import shutil
import sys
from importlib.resources import files
from pathlib import Path
from typing import Iterable

_PACKAGE = "promptukit.claude_commands"
_SUFFIX = ".md"


def _resource_dir() -> Path:
    return Path(str(files(_PACKAGE)))


def list_commands() -> list[str]:
    """Return sorted command names (without the .md extension)."""
    return sorted(p.stem for p in _resource_dir().glob(f"*{_SUFFIX}"))


def get_command_path(name: str) -> Path:
    """Return the on-disk Path to the bundled command file."""
    path = _resource_dir() / f"{name}{_SUFFIX}"
    if not path.is_file():
        raise FileNotFoundError(
            f"No bundled Claude command named {name!r}. "
            f"Available: {', '.join(list_commands()) or '(none)'}"
        )
    return path


def get_command(name: str) -> str:
    """Return the markdown content of the named command."""
    return get_command_path(name).read_text(encoding="utf-8")


def install(
    dest: Path | str | None = None,
    force: bool = False,
    names: Iterable[str] | None = None,
) -> list[Path]:
    """Copy bundled commands into a `.claude/commands/`-style directory.

    Default dest: `<cwd>/.claude/commands`.
    Existing files are skipped unless `force=True`.
    Returns the list of paths actually written.
    """
    target = Path(dest) if dest is not None else Path.cwd() / ".claude" / "commands"
    target.mkdir(parents=True, exist_ok=True)

    selected = list(names) if names else list_commands()
    written: list[Path] = []
    for name in selected:
        src = get_command_path(name)
        dst = target / src.name
        if dst.exists() and not force:
            continue
        shutil.copyfile(src, dst)
        written.append(dst)
    return written


def _cli(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="promptukit-claude-commands",
        description="Access bundled Claude Code slash-command prompts.",
    )
    sub = parser.add_subparsers(dest="cmd", required=True)

    sub.add_parser("list", help="List bundled command names.")

    show = sub.add_parser("show", help="Print a command's markdown to stdout.")
    show.add_argument("name")

    inst = sub.add_parser(
        "install",
        help="Copy commands into a .claude/commands/ directory "
        "(default: ./.claude/commands).",
    )
    inst.add_argument(
        "--dest",
        type=Path,
        default=None,
        help="Target directory (default: ./.claude/commands).",
    )
    inst.add_argument(
        "--force",
        action="store_true",
        help="Overwrite existing files.",
    )
    inst.add_argument(
        "names",
        nargs="*",
        help="Specific command names to install (default: all).",
    )

    args = parser.parse_args(argv)

    if args.cmd == "list":
        for name in list_commands():
            print(name)
        return 0

    if args.cmd == "show":
        try:
            sys.stdout.write(get_command(args.name))
        except FileNotFoundError as exc:
            print(str(exc), file=sys.stderr)
            return 1
        return 0

    if args.cmd == "install":
        try:
            written = install(
                dest=args.dest, force=args.force, names=args.names or None
            )
        except FileNotFoundError as exc:
            print(str(exc), file=sys.stderr)
            return 1
        if not written:
            print(
                "Nothing written (all targets already exist; pass --force to overwrite)."
            )
            return 0
        for p in written:
            print(f"wrote {p}")
        return 0

    return 2


def main() -> None:  # entry-point shim
    raise SystemExit(_cli())


__all__ = [
    "list_commands",
    "get_command",
    "get_command_path",
    "install",
    "main",
]
