#!/usr/bin/env python3
"""Interactively add a trivia question to assets/trivia.json.

Thin shim over :mod:`promptukit.questions.add_question` that defaults the
bank path to this repo's ``assets/trivia.json``.
"""
import sys
from pathlib import Path

from promptukit.questions import add_question

add_question.DEFAULT_BANK_PATH = (
    Path(__file__).resolve().parent.parent / "promptukit" / "data" / "question_banks" / "jrb_industries_trivia.json"
)

main = add_question.main


if __name__ == "__main__":
    sys.exit(main())
