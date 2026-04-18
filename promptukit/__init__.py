"""promptukit — utilities for building question banks and exam documents."""

from promptukit.utils.cli_helpers import load, save, pick, confirm, load_resource
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
]

__version__ = "0.1.0"
