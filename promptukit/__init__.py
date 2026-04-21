"""promptukit — utilities for building question banks and exam documents."""

from promptukit.utils.cli_helpers import load, save, pick, confirm, load_resource

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
]

from importlib.metadata import version, PackageNotFoundError
try:
    __version__ = version("promptukit")
except PackageNotFoundError:
    __version__ = "unknown"
