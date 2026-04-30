"""Generate an exam Markdown document from a promptukit question bank.

Mirrors the CLI shape of ``create_exam.py`` but emits a ``.md`` file that a
professor can edit before rendering.  Because the Markdown is the intermediate
step, the typical workflow is:

1. Export JSON → Markdown (this module)
2. Edit the ``.md`` in any text editor
3. Convert Markdown → PDF via pandoc (``--to-pdf``) or another tool

Supports all question types: MultipleChoice, TrueFalse, ShortAnswer,
FillInTheBlank, Matching, Calculation.

Answer modes (``--answers``):
  none    — no answers shown (default; student-facing)
  inline  — answer printed after each question (instructor preview)
  key     — numbered answer key appended at the end of the document

Pandoc conversion (``--to-pdf``):
  Shells out to ``pandoc``, which must be installed separately
  (https://pandoc.org/installing.html).  The Markdown file is always kept.

Run:
  python -m promptukit.exams.create_exam_md -q bank.json -o exam.md
  create-exam-md -q bank.json -o exam.md --answers key
  create-exam-md -q bank.json -o exam.md --to-pdf          # also produce exam.pdf
  create-exam-md -q bank.json -o exam.md --to-pdf final.pdf
"""

from __future__ import annotations

import argparse
import html as _html_mod
import json
import re
import shutil
import subprocess
import sys
import unicodedata
from collections import OrderedDict
from pathlib import Path
from typing import Any, List, Optional, Tuple

from promptukit.exams.create_exam import (
    DEFAULT_METADATA,
    effective_metadata,
    load_metadata_from_json,
    questions_artifact,
    save_json_artifact,
)
from promptukit.questions.question_models import (
    Calculation,
    FillInTheBlank,
    Matching,
    MultipleChoice,
    Question,
    ShortAnswer,
    TrueFalse,
)

ANSWER_MODES = ("none", "inline", "key")
CHOOSE_ONE_MARK = "\u25cb"
CHOOSE_MULTIPLE_MARK = "\u2610"
FILL_BLANK_LINE = "____________________"
SHORT_ANSWER_LINE = "________________________________________________________________________________"
CHOOSE_MULTIPLE_TYPES = {
    "choosemultiple",
    "multipleanswer",
    "multipleresponse",
    "multipleselect",
    "selectallthatapply",
}

_TAG_RE = re.compile(r"<[^>]+>")
_ENTITY_MAP: dict[str, str] = {
    "&mdash;": "—",
    "&ndash;": "–",
    "&minus;": "−",
    "&nbsp;": " ",
    "&deg;": "°",
    "&Delta;": "Δ",
    "&phi;": "φ",
    "&pi;": "π",
    "&times;": "×",
    "&plusmn;": "±",
    "&amp;": "&",
    "&lt;": "<",
    "&gt;": ">",
    "&quot;": '"',
    "&alpha;": "α",
    "&beta;": "β",
    "&gamma;": "γ",
    "&lambda;": "λ",
    "&mu;": "μ",
    "&sigma;": "σ",
    "&Sigma;": "Σ",
    "&omega;": "ω",
    "&Omega;": "Ω",
    "&infin;": "∞",
    "&le;": "≤",
    "&ge;": "≥",
    "&ne;": "≠",
    "&asymp;": "≈",
}
_LEADING_NUMBER_RE = re.compile(r"^\s*\d+\.\s*")
_LETTER_PREFIX_RE = re.compile(r"^[A-Za-z][\)\.\s]+")


# --- Text conversion --------------------------------------------------------

def md_safe_text(value: Any) -> str:
    """Convert reportlab-style markup to Markdown-compatible text.

    - Resolves HTML entities to Unicode characters
    - Converts ``<b>`` / ``<i>`` to Markdown bold / italic
    - Normalises ``<super>`` → ``<sup>`` (valid HTML in most MD renderers)
    - Leaves ``<sub>`` / ``<sup>`` intact; strips all other tags
    """
    s = str(value if value is not None else "")
    s = unicodedata.normalize("NFC", s)
    for ent, ch in _ENTITY_MAP.items():
        s = s.replace(ent, ch)
    s = _html_mod.unescape(s)
    s = re.sub(r"<b>(.*?)</b>", r"**\1**", s, flags=re.IGNORECASE | re.DOTALL)
    s = re.sub(r"<i>(.*?)</i>", r"*\1*", s, flags=re.IGNORECASE | re.DOTALL)
    s = re.sub(r"<super>(.*?)</super>", r"<sup>\1</sup>", s, flags=re.IGNORECASE | re.DOTALL)
    # Strip tags other than <sub> and <sup>/<sup>
    s = re.sub(r"<(?!/?su[bp])[^>]+>", "", s)
    return s


# --- Answer extraction ------------------------------------------------------

def _answer_text(q: Any) -> Optional[str]:
    """Return a human-readable answer string, or None if unavailable."""
    if isinstance(q, MultipleChoice):
        if q.answer_index is not None and 0 <= q.answer_index < len(q.choices):
            return f"{chr(ord('A') + q.answer_index)}) {md_safe_text(q.choices[q.answer_index])}"
        if q.answer_text is not None:
            return md_safe_text(q.answer_text)
        return None
    if isinstance(q, TrueFalse):
        return "True" if q.answer else "False"
    if isinstance(q, ShortAnswer):
        return md_safe_text(q.answer) if q.answer else None
    if isinstance(q, FillInTheBlank):
        return ", ".join(md_safe_text(a) for a in q.answers) if q.answers else None
    if isinstance(q, Matching):
        if q.pairs:
            return "; ".join(
                f"{md_safe_text(p[0])} → {md_safe_text(p[1])}"
                for p in q.pairs if len(p) == 2
            )
        return None
    if isinstance(q, Calculation):
        ans = q.answer
        unit = getattr(q, "unit", None)
        if ans is not None:
            return f"{ans} {md_safe_text(unit)}" if unit else str(ans)
        return None
    # Plain dict fallback
    if isinstance(q, dict):
        ans = q.get("answer")
        if ans is None:
            return None
        choices = q.get("choices") or []
        if isinstance(ans, int) and 0 <= ans < len(choices):
            return f"{chr(ord('A') + ans)}) {md_safe_text(choices[ans])}"
        return md_safe_text(str(ans))
    return None


# --- Per-question rendering -------------------------------------------------

def _letter(idx: int) -> str:
    return chr(ord("A") + idx)


def _format_choice(idx: int, raw: Any, *, label: bool = True) -> str:
    raw_text = str(raw).strip()
    safe = md_safe_text(raw_text)
    if not label:
        return safe
    if _LETTER_PREFIX_RE.match(raw_text):
        return safe
    return f"{_letter(idx)}) {safe}"


def _raw_question_dict(q: Any) -> dict[str, Any]:
    raw = getattr(q, "_raw", None)
    return raw if isinstance(raw, dict) else q if isinstance(q, dict) else {}


def _is_choose_multiple(q: Any) -> bool:
    raw = _raw_question_dict(q)
    qtype = str(raw.get("question_type") or raw.get("type") or "").lower()
    qtype = re.sub(r"[^a-z]", "", qtype)
    if qtype in CHOOSE_MULTIPLE_TYPES:
        return True
    if raw.get("multiple") is True or raw.get("multi_select") is True:
        return True
    return isinstance(raw.get("answer"), list) and bool(raw.get("choices"))


def _choice_marker(q: Any) -> str:
    return CHOOSE_MULTIPLE_MARK if _is_choose_multiple(q) else CHOOSE_ONE_MARK


def _render_choice_lines(q: Any, raw_choices: List[Any], *, label: bool = True) -> List[str]:
    marker = _choice_marker(q)
    lines: List[str] = []
    for j, choice in enumerate(raw_choices):
        lines.extend([f"{marker} {_format_choice(j, choice, label=label)}", ""])
    return lines


def _render_answer_space_lines(unit: str = "") -> List[str]:
    suffix = f" {unit}" if unit else ""
    return [
        "*Answer:*",
        "",
        f"{SHORT_ANSWER_LINE}{suffix}",
        "",
        SHORT_ANSWER_LINE,
        "",
    ]


def _render_fill_blank_text(text: str) -> str:
    return text.replace(FillInTheBlank.BLANK_TOKEN, FILL_BLANK_LINE)


def _render_question_lines(q: Any, number: int, answers: str = "none") -> List[str]:
    """Return Markdown lines for one question."""
    lines: List[str] = []

    # Question text (strip leading "N. " added by the bank or prior export)
    if isinstance(q, Question):
        q_text = md_safe_text(q.text)
    else:
        q_text = md_safe_text(
            q.get("q") or q.get("prompt") or q.get("question") or q.get("text") or ""
        )
    q_text = _LEADING_NUMBER_RE.sub("", q_text).strip()
    if isinstance(q, FillInTheBlank):
        q_text = _render_fill_blank_text(q_text)
    lines.append(f"**{number}.** {q_text}")
    lines.append("")

    if isinstance(q, TrueFalse):
        lines += _render_choice_lines(q, ["True", "False"], label=False)
    elif isinstance(q, ShortAnswer):
        lines += _render_answer_space_lines()
    elif isinstance(q, FillInTheBlank):
        pass
    elif isinstance(q, Matching) and q.pairs:
        lines.append("| | Left | Right |")
        lines.append("|---|------|-------|")
        for pair in q.pairs:
            if len(pair) == 2:
                lines.append(f"| ___ | {md_safe_text(pair[0])} | {md_safe_text(pair[1])} |")
        lines.append("")
    elif isinstance(q, Calculation):
        unit = getattr(q, "unit", None)
        lines += _render_answer_space_lines(md_safe_text(unit) if unit else "")
    else:
        # MultipleChoice or plain dict with choices
        if isinstance(q, MultipleChoice):
            raw_choices = q.choices
        else:
            raw_choices = q.get("choices") or []
        lines += _render_choice_lines(q, raw_choices)

    if answers == "inline":
        ans = _answer_text(q)
        if ans:
            lines += [f"> **Answer:** {ans}", ""]

    return lines


# --- Section normalisation --------------------------------------------------

def _process_sections(sections_or_questions: Any) -> List[dict]:
    """Normalise any input shape into a list of {title, questions} dicts."""
    if isinstance(sections_or_questions, dict):
        if "sections" in sections_or_questions:
            return sections_or_questions["sections"]
        if "questions" in sections_or_questions:
            return [{"title": "", "questions": sections_or_questions["questions"]}]
    if isinstance(sections_or_questions, list):
        if (
            sections_or_questions
            and isinstance(sections_or_questions[0], dict)
            and "questions" in sections_or_questions[0]
        ):
            return sections_or_questions
        # Flat list — group by category if present
        if any(isinstance(q, dict) and q.get("category") for q in sections_or_questions):
            groups: OrderedDict = OrderedDict()
            for q in sections_or_questions:
                cat = (q.get("category") if isinstance(q, dict) else None) or "Uncategorized"
                groups.setdefault(cat, []).append(q)
            return [{"title": t, "questions": qs} for t, qs in groups.items()]
        return [{"title": "", "questions": sections_or_questions}]
    return [{"title": "", "questions": []}]


# --- JSON loading (preserves answer fields) ---------------------------------

def _read_question_bank(path: str) -> Any:
    """Load a JSON bank, preserving per-question fields (including answers).

    Accepts the same top-level layouts as ``create_exam.load_questions_from_json``
    but does *not* normalise per-question dicts so that answer data is retained.
    """
    data = _read_json_file(path, "Question bank file")

    if isinstance(data, list):
        return {"questions": [q for q in data if isinstance(q, dict)]}
    if not isinstance(data, dict):
        return {"questions": []}
    if "sections" in data and isinstance(data["sections"], list):
        return data
    if "questions" in data and isinstance(data["questions"], list):
        return {"questions": [q for q in data["questions"] if isinstance(q, dict)]}
    return {"questions": []}


def _read_metadata_file(path: str) -> dict:
    p = _ensure_input_file(path, "Metadata file")
    try:
        return load_metadata_from_json(str(p))
    except json.JSONDecodeError as exc:
        raise ValueError(
            f"Metadata file is not valid JSON: {p} "
            f"(line {exc.lineno}, column {exc.colno}: {exc.msg})"
        ) from exc


def _ensure_input_file(path: str, label: str) -> Path:
    p = Path(path)
    if not p.exists():
        raise FileNotFoundError(f"{label} not found: {p}")
    if not p.is_file():
        raise FileNotFoundError(f"{label} is not a file: {p}")
    return p


def _read_json_file(path: str, label: str) -> Any:
    p = _ensure_input_file(path, label)
    try:
        with p.open("r", encoding="utf-8") as fh:
            return json.load(fh)
    except json.JSONDecodeError as exc:
        raise ValueError(
            f"{label} is not valid JSON: {p} "
            f"(line {exc.lineno}, column {exc.colno}: {exc.msg})"
        ) from exc


def _display_exam_type(meta: dict) -> str:
    exam_type = md_safe_text(meta.get("exam_type") or "")
    default_exam_type = md_safe_text(DEFAULT_METADATA.get("exam_type") or "")
    if exam_type == default_exam_type:
        return ""
    return exam_type


# --- Public API -------------------------------------------------------------

def build_exam_md(
    sections_or_questions: Any,
    output_path,
    metadata=None,
    answers: str = "none",
) -> Path:
    """Write an exam Markdown file from a question bank.

    Parameters
    ----------
    sections_or_questions:
        Same shapes accepted by ``build_exam_pdf``: a dict with ``sections`` or
        ``questions`` key, a flat list of question dicts, or a list of section
        dicts.
    output_path:
        Destination ``.md`` file path.
    metadata:
        Optional dict (or None) merged with DEFAULT_METADATA.
    answers:
        One of ``"none"`` (default), ``"inline"`` (answer after each question),
        or ``"key"`` (answer key appended at the end).
    """
    if answers not in ANSWER_MODES:
        raise ValueError(f"answers must be one of {ANSWER_MODES}, got {answers!r}")

    p = Path(output_path)
    parent = p.parent
    if parent and not parent.exists():
        parent.mkdir(parents=True, exist_ok=True)
    elif parent and not parent.is_dir():
        raise OSError(f"Output parent exists and is not a directory: {parent}")

    meta = effective_metadata(metadata)
    sections = _process_sections(sections_or_questions)

    lines: List[str] = []

    # --- Title block ---
    lines.append(f"# {md_safe_text(meta['title'])}")
    lines.append("")
    subtitle_parts = [md_safe_text(meta["institution"]), md_safe_text(meta["instructor"])]
    subtitle = " — ".join(part for part in subtitle_parts if part)
    if subtitle:
        lines.append(subtitle)
        lines.append("")
    exam_type = _display_exam_type(meta)
    if exam_type:
        lines.append(f"*{exam_type}*")
        lines.append("")

    # --- Header fields table ---
    header_fields = meta.get("header_fields") or []
    if header_fields:
        first_row = header_fields[0]
        num_cols = len(first_row)
        lines.append("| " + " | ".join(md_safe_text(cell) for cell in first_row) + " |")
        lines.append("| " + " | ".join(["---"] * num_cols) + " |")
        for row in header_fields[1:]:
            lines.append("| " + " | ".join(md_safe_text(cell) for cell in row) + " |")
        lines.append("")

    # --- Instructions ---
    instructions = md_safe_text(meta.get("instructions") or "")
    if instructions:
        lines.append(f"> {instructions}")
        lines.append("")

    lines.append("---")
    lines.append("")

    # --- Questions ---
    answer_key: List[Tuple[int, Optional[str]]] = []
    question_counter = 1

    for sec in sections:
        sec_title = sec.get("title") or ""
        if sec_title:
            lines.append(f"## {md_safe_text(sec_title)}")
            lines.append("")

        for q_raw in sec.get("questions") or []:
            # Upgrade plain dict to Question object when possible (enables typed rendering)
            q: Any = q_raw
            if isinstance(q_raw, dict):
                try:
                    q = Question.from_json(q_raw)
                except Exception:
                    q = q_raw

            lines.extend(_render_question_lines(q, question_counter, answers=answers))

            if answers == "key":
                answer_key.append((question_counter, _answer_text(q)))

            question_counter += 1

    # --- Footer ---
    lines.append("---")
    lines.append("")
    footer = md_safe_text(meta.get("footer") or "")
    if footer:
        # md_safe_text already converts <b> tags; avoid double-wrapping
        if not footer.startswith("**"):
            footer = f"**{footer}**"
        lines.append(footer)
        lines.append("")

    # --- Answer key ---
    if answers == "key" and answer_key:
        lines += ["", "---", "", "## Answer Key", ""]
        for num, ans in answer_key:
            lines.append(f"{num}. {ans if ans else '—'}")
        lines.append("")

    p.write_text("\n".join(lines), encoding="utf-8")
    print(f"Exam Markdown created at: {p}")
    return p


# --- Pandoc conversion ------------------------------------------------------

def convert_md_to_pdf(md_path: Path, pdf_path: Path) -> None:
    """Convert a Markdown file to PDF via pandoc.

    Raises ``FileNotFoundError`` if pandoc is not on PATH, or
    ``subprocess.CalledProcessError`` if pandoc exits non-zero.
    """
    if shutil.which("pandoc") is None:
        raise FileNotFoundError(
            "pandoc not found on PATH. Install it from https://pandoc.org/installing.html"
        )
    cmd = ["pandoc", str(md_path), "-o", str(pdf_path), "--standalone"]
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        raise subprocess.CalledProcessError(
            result.returncode, cmd, output=result.stdout, stderr=result.stderr
        )
    print(f"Exam PDF created at: {pdf_path}")


# --- CLI --------------------------------------------------------------------

def main(argv: Optional[List[str]] = None) -> int:
    parser = argparse.ArgumentParser(
        description="Create an exam Markdown file from a promptukit question bank."
    )
    parser.add_argument("-q", "--questions", required=True, help="Path to JSON question bank file")
    parser.add_argument("-o", "--output", required=True, help="Output .md filename")
    parser.add_argument("-m", "--metadata", "--setup", help="Path to JSON metadata/setup file", default=None)
    parser.add_argument(
        "--answers",
        choices=ANSWER_MODES,
        default="none",
        help="Answer mode: none (default), inline (after each question), key (appended answer key)",
    )
    parser.add_argument(
        "--to-pdf",
        metavar="PDF_PATH",
        nargs="?",
        const="",
        default=None,
        help=(
            "Convert the generated Markdown to PDF via pandoc. "
            "Optionally specify output path; defaults to the .md path with a .pdf extension. "
            "Requires pandoc on PATH (https://pandoc.org/installing.html)."
        ),
    )
    parser.add_argument("--save-questions", help="Write the normalised question artifact", default=None)
    parser.add_argument("--save-setup", help="Write the effective metadata artifact", default=None)
    args = parser.parse_args(argv)

    try:
        questions_to_use = _read_question_bank(args.questions)
        meta = _read_metadata_file(args.metadata) if args.metadata else None
    except (FileNotFoundError, OSError, ValueError) as e:
        print(f"Error: {e}", file=sys.stderr)
        return 1

    if args.save_questions:
        save_json_artifact(args.save_questions, questions_artifact(questions_to_use))
        print(f"Question artifact written to: {args.save_questions}")
    if args.save_setup:
        save_json_artifact(args.save_setup, effective_metadata(meta))
        print(f"Setup artifact written to: {args.save_setup}")

    try:
        md_path = build_exam_md(questions_to_use, args.output, metadata=meta, answers=args.answers)
    except Exception as e:
        print(f"Error creating Markdown: {e}", file=sys.stderr)
        return 1

    if args.to_pdf is not None:
        pdf_path = Path(args.to_pdf) if args.to_pdf else md_path.with_suffix(".pdf")
        try:
            convert_md_to_pdf(md_path, pdf_path)
        except FileNotFoundError as e:
            print(f"Error: {e}", file=sys.stderr)
            return 1
        except subprocess.CalledProcessError as e:
            print(f"pandoc failed (exit {e.returncode}):", file=sys.stderr)
            if e.stderr:
                print(e.stderr, file=sys.stderr)
            return 1

    return 0


if __name__ == "__main__":
    sys.exit(main())
