"""
Generate a pub-quiz style group trivia PDF.

Each round becomes a single printable sheet that a team fills out and turns in.
Sheets are independently gradeable: every round carries its own team-name and
score fields at the top so graders can separate and score rounds in parallel.

Input JSON layout (preferred)::

    {
      "title": "JRB Industries Pub Quiz",
      "rounds": [
        {
          "title": "Round 1: Motorsport",
          "theme": "Open wheel, closed wheel, and everything in between.",
          "questions": [
            {"prompt": "..."},
            {"prompt": "...", "choices": ["A", "B", "C", "D"]}
          ]
        }
      ]
    }

``sections`` and ``categories`` are accepted as aliases for ``rounds``.
A flat ``questions`` list with ``round`` / ``category`` keys is also grouped.

Requires: reportlab  (pip install reportlab)
Run: python -m promptukit.exams.create_pub_quiz -q pubquiz.json -o pubquiz.pdf
"""

from reportlab.lib.pagesizes import letter
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, KeepTogether, PageBreak
)
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.lib.enums import TA_CENTER, TA_JUSTIFY, TA_LEFT
from reportlab.lib import colors
import argparse
import json
import re
import sys
from collections import OrderedDict
from pathlib import Path
from xml.sax.saxutils import escape as _xml_escape


styles = getSampleStyleSheet()

title_style = ParagraphStyle('QuizTitle', parent=styles['Title'],
    fontSize=18, spaceAfter=2, alignment=TA_CENTER)
round_title_style = ParagraphStyle('RoundTitle', parent=styles['Heading1'],
    fontSize=15, spaceBefore=2, spaceAfter=2, alignment=TA_CENTER,
    textColor=colors.HexColor('#1a1a1a'))
theme_style = ParagraphStyle('RoundTheme', parent=styles['Italic'],
    fontSize=10, spaceAfter=8, alignment=TA_CENTER, textColor=colors.HexColor('#444444'))
subtitle_style = ParagraphStyle('QuizSubtitle', parent=styles['Normal'],
    fontSize=10, spaceAfter=2, alignment=TA_CENTER)
instructions_style = ParagraphStyle('Instructions', parent=styles['Normal'],
    fontSize=9, spaceAfter=6, leftIndent=12, rightIndent=12, alignment=TA_JUSTIFY)
question_style = ParagraphStyle('Question', parent=styles['Normal'],
    fontSize=11, spaceBefore=10, spaceAfter=2, fontName='Helvetica-Bold',
    leading=14)
choice_style = ParagraphStyle('Choice', parent=styles['Normal'],
    fontSize=10, spaceBefore=1, spaceAfter=1, leftIndent=24)
answer_line_style = ParagraphStyle('AnswerLine', parent=styles['Normal'],
    fontSize=10, spaceBefore=4, spaceAfter=2, leftIndent=24,
    fontName='Helvetica')
footer_style = ParagraphStyle('RoundFooter', parent=styles['Normal'],
    fontSize=10, alignment=TA_CENTER, fontName='Helvetica-Bold', spaceBefore=12)


DEFAULT_METADATA = {
    "title": "Pub Quiz",
    "institution": "",
    "host": "",
    "quiz_type": "Group Trivia",
    "instructions": (
        "<b>Instructions:</b> Work as a team. Write your answer on the line "
        "under each question. For multiple-choice questions, write the letter "
        "of your choice. No phones, no internet. Turn in this sheet at the "
        "end of the round."
    ),
    "answer_prompt": "Answer:",
    "score_label": "Score",
    "team_label": "Team Name",
    "date_label": "Date",
    "round_end_text": "&mdash; END OF ROUND {n} &mdash;",
}


def _escape_if_needed(text):
    """Escape XML special chars so ReportLab's Paragraph parser doesn't choke."""
    return _xml_escape(str(text))


def _question_block(q_data, counter, answer_prompt):
    """Render one question as a KeepTogether flowable group."""
    if isinstance(q_data, dict):
        q_text = (q_data.get('q') or q_data.get('prompt')
                  or q_data.get('question') or q_data.get('text') or '')
        choices = q_data.get('choices') or q_data.get('options') or []
        qtype = (q_data.get('question_type') or '').lower()
    else:
        q_text = str(q_data)
        choices = []
        qtype = ''

    if re.match(r'^\s*\d+\.', str(q_text).strip()) is None:
        q_text = f"{counter}. {q_text}"

    block = [Paragraph(_escape_if_needed(q_text), question_style)]

    if choices:
        for j, c in enumerate(choices):
            chs = _escape_if_needed(str(c).strip())
            if re.match(r'^[A-Za-z][\)\.\s]+', chs):
                block.append(Paragraph(chs, choice_style))
            else:
                label = chr(ord('A') + (j % 26))
                block.append(Paragraph(f"{label}) {chs}", choice_style))
        blank = "_____"
    elif qtype in ('truefalse', 'true_false', 'true/false', 'tf'):
        blank = "T  /  F"
    else:
        blank = "_" * 60

    block.append(Paragraph(
        f"<b>{_escape_if_needed(answer_prompt)}</b> &nbsp; {blank}",
        answer_line_style,
    ))
    return KeepTogether(block)


def _round_header(meta, round_title, round_theme, question_count):
    """Build the team-name / date / score table shown at the top of each round sheet."""
    team_cell = f"{meta['team_label']}: ______________________________________"
    date_cell = f"{meta['date_label']}: ____________"
    score_cell = f"{meta['score_label']}: _____ / {question_count}"

    header_table = Table(
        [[team_cell, date_cell, score_cell]],
        colWidths=[3.6 * inch, 1.6 * inch, 1.8 * inch],
    )
    header_table.setStyle(TableStyle([
        ('FONTNAME', (0, 0), (-1, -1), 'Helvetica'),
        ('FONTSIZE', (0, 0), (-1, -1), 10),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
        ('TOPPADDING', (0, 0), (-1, -1), 6),
        ('BOX', (0, 0), (-1, -1), 1, colors.black),
        ('INNERGRID', (0, 0), (-1, -1), 0.5, colors.grey),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
    ]))

    flowables = []
    flowables.append(Paragraph(_escape_if_needed(meta['title']), title_style))
    sub_parts = [_escape_if_needed(p) for p in (meta.get('institution'), meta.get('host')) if p]
    if sub_parts:
        flowables.append(Paragraph(" &mdash; ".join(sub_parts), subtitle_style))
    flowables.append(Spacer(1, 4))
    flowables.append(Paragraph(_escape_if_needed(round_title), round_title_style))
    if round_theme:
        flowables.append(Paragraph(_escape_if_needed(round_theme), theme_style))
    flowables.append(Spacer(1, 4))
    flowables.append(header_table)
    flowables.append(Spacer(1, 6))
    flowables.append(Paragraph(meta['instructions'], instructions_style))
    flowables.append(Spacer(1, 2))
    return flowables


def build_pub_quiz_pdf(rounds, output_path, metadata=None):
    p = Path(output_path)
    parent = p.parent
    if parent and not parent.exists():
        parent.mkdir(parents=True, exist_ok=True)
    elif parent and not parent.is_dir():
        raise OSError(f"Output parent exists and is not a directory: {parent}")

    doc = SimpleDocTemplate(
        str(p), pagesize=letter,
        topMargin=0.55 * inch, bottomMargin=0.55 * inch,
        leftMargin=0.75 * inch, rightMargin=0.75 * inch,
    )

    meta = DEFAULT_METADATA.copy()
    if metadata:
        meta.update({k: v for k, v in metadata.items() if v is not None})

    story = []
    total_rounds = len(rounds)

    for r_idx, rnd in enumerate(rounds, start=1):
        r_title = rnd.get('title') or f"Round {r_idx}"
        r_theme = rnd.get('theme') or rnd.get('description') or ''
        questions = rnd.get('questions') or []

        if re.match(r'^\s*round\s*\d', r_title.strip(), re.IGNORECASE) is None:
            r_title = f"Round {r_idx}: {r_title}"

        story.extend(_round_header(meta, r_title, r_theme, len(questions)))

        counter = 1
        for q in questions:
            story.append(_question_block(q, counter, meta['answer_prompt']))
            counter += 1

        story.append(Paragraph(
            meta['round_end_text'].format(n=r_idx),
            footer_style,
        ))

        if r_idx < total_rounds:
            story.append(PageBreak())

    try:
        doc.build(story)
    except Exception as e:
        print(f"Failed to build PDF at {output_path}: {e}")
        raise
    print(f"Pub quiz PDF created at: {output_path} ({total_rounds} round(s))")


def load_rounds_from_json(path):
    """Load a JSON file and normalize to a list of round dicts.

    Accepts ``rounds``, ``sections``, or ``categories`` keys, or a flat
    ``questions`` array with ``round`` / ``category`` keys.
    """
    with Path(path).open('r', encoding='utf-8') as fh:
        data = json.load(fh)

    if not isinstance(data, (dict, list)):
        raise ValueError(f"Unsupported JSON root type: {type(data).__name__}")

    if isinstance(data, dict):
        for key in ('rounds', 'sections', 'categories'):
            if key in data:
                raw = data.get(key) or []
                if isinstance(raw, list) and all(isinstance(x, str) for x in raw) \
                        and isinstance(data.get('questions'), list):
                    return _group_flat_into_rounds(data['questions'], round_names=raw)
                return [_normalize_round(r) for r in raw]

        if isinstance(data.get('questions'), list):
            return _group_flat_into_rounds(data['questions'])

    elif isinstance(data, list):
        if data and isinstance(data[0], dict) and 'questions' in data[0]:
            return [_normalize_round(r) for r in data]
        return _group_flat_into_rounds(data)

    return []


def _normalize_round(sec):
    if not isinstance(sec, dict):
        return {'title': str(sec), 'theme': '', 'questions': []}
    title = sec.get('title') or sec.get('name') or sec.get('label') or ''
    theme = sec.get('theme') or sec.get('description') or ''
    qitems = sec.get('questions') or sec.get('items') or []
    return {
        'title': title,
        'theme': theme,
        'questions': [_normalize_question(q) for q in qitems],
    }


def _normalize_question(it):
    if isinstance(it, str):
        return {'q': it, 'choices': []}
    prompt = (it.get('prompt') or it.get('q') or it.get('question')
              or it.get('text') or '')
    choices = it.get('choices') or it.get('options') or it.get('answers') or []
    out = {'q': prompt, 'choices': list(choices)}
    if it.get('question_type'):
        out['question_type'] = it['question_type']
    for passthrough in ('round', 'category', 'difficulty'):
        if it.get(passthrough):
            out[passthrough] = it[passthrough]
    return out


def _group_flat_into_rounds(flat_qs, round_names=None):
    groups = OrderedDict()
    if round_names:
        for name in round_names:
            groups[name] = []

    for it in flat_qs:
        nq = _normalize_question(it)
        key = nq.get('round') or nq.get('category') or 'Round 1'
        groups.setdefault(key, []).append(nq)

    return [{'title': title, 'theme': '', 'questions': qs}
            for title, qs in groups.items() if qs]


def load_metadata_from_json(path):
    with Path(path).open('r', encoding='utf-8') as fh:
        data = json.load(fh)
    if not isinstance(data, dict):
        raise ValueError(f"Metadata file must be a JSON object, got {type(data).__name__}")
    merged = dict(DEFAULT_METADATA)
    merged.update({k: v for k, v in data.items() if v is not None})
    return merged


def main():
    parser = argparse.ArgumentParser(
        description="Create a pub-quiz PDF (one sheet per round)."
    )
    parser.add_argument('-q', '--questions', required=True,
                        help='Path to JSON file with rounds/questions')
    parser.add_argument('-o', '--output', default='pub_quiz.pdf',
                        help='Output PDF filename')
    parser.add_argument('-m', '--metadata', default=None,
                        help='Path to JSON metadata file (title, host, etc.)')
    args = parser.parse_args()

    rounds = load_rounds_from_json(args.questions)
    if not rounds:
        print(f"No rounds found in {args.questions}", file=sys.stderr)
        sys.exit(1)

    meta = load_metadata_from_json(args.metadata) if args.metadata else None

    try:
        build_pub_quiz_pdf(rounds, args.output, metadata=meta)
    except Exception as e:
        print(f"Error creating pub quiz PDF: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == '__main__':
    main()
