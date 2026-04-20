#!/usr/bin/env python3
"""Extract information from assets/trivia.json.

Thin shim over :mod:`promptukit.questions.extract_question` that defaults
the bank path to this repo's ``assets/trivia.json``.
"""
from pathlib import Path

from promptukit.questions import extract_question

extract_question.DEFAULT_BANK_PATH = (
    Path(__file__).resolve().parent.parent / "promptukit" / "data" / "question_banks" / "jrb_industries_trivia.json"
)

main = extract_question.main


if __name__ == "__main__":
    raise SystemExit(main())
