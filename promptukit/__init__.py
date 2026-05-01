"""promptukit — utilities for building question banks and exam documents."""

from importlib.metadata import PackageNotFoundError, version as package_version
from pathlib import Path
import tomllib

from promptukit.utils.cli_helpers import load, save, pick, confirm, load_resource
from promptukit.gui import launch as launch_gui
from promptukit import questions, exams, utils

__all__ = [
    # subpackages
    "questions",
    "exams",
    "utils",
    # flat re-exports from utils
    "load",
    "save",
    "pick",
    "confirm",
    "load_resource",
    # gui
    "launch_gui",
]


def _resolve_version() -> str:
    # Use installed package metadata when available.
    try:
        return package_version("promptukit")
    except PackageNotFoundError:
        pass

    # Fallback for local source usage: read Poetry version from pyproject.toml.
    pyproject = Path(__file__).resolve().parent.parent / "pyproject.toml"
    data = tomllib.loads(pyproject.read_text(encoding="utf-8"))
    return data["tool"]["poetry"]["version"]


__version__ = _resolve_version()
