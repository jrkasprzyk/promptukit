"""Package marker for the scripts module so it can be installed editable.

This file intentionally left minimal.
"""

__all__ = [
    "add_trivia",
    "extract_trivia",
    "cli_helpers",
]

# Package version. Kept here for simple runtime access; the canonical
# version is managed in `pyproject.toml` for Poetry packaging.
__version__ = "0.1.0"
