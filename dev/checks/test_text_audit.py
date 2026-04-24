import json
from pathlib import Path

from promptukit.exams import create_exam
from promptukit.questions import question_bank, text_audit
from promptukit.utils import html_md_convert
from promptukit.utils import json_tools


def _write_json(path: Path, data) -> None:
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def _hostile_bank():
    hostile_prompt = (
        "Cafe\u0301\u00a0zero\u200b "
        "R\u00c3\u00a4ikk\u00c3\u00b6nen "
        "\u00e2\u20ac\u201d "
        "AT&T <vector> 5 < 10 0\u00b0C x\u00b2 9\u00be"
    )
    return {
        "categories": ["general"],
        "questions": [
            {
                "id": "general_001",
                "category": "general",
                "difficulty": "easy",
                "prompt": hostile_prompt,
                "choices": ["A", "B", "C", "D"],
                "answer": 0,
            }
        ],
    }


def test_text_audit_finds_and_fixes_common_hazards(tmp_path: Path):
    src = tmp_path / "bad.json"
    dest = tmp_path / "fixed.json"
    _write_json(src, _hostile_bank())

    issues = text_audit.audit_file(src)
    codes = {issue.code for issue in issues}
    assert {"not_nfc", "nonbreaking_space", "invisible_control", "suspect_mojibake"} <= codes

    changed = text_audit.fix_file(src, dest)
    assert changed is True
    assert text_audit.audit_file(dest) == []

    fixed = json.loads(dest.read_text(encoding="utf-8"))
    prompt = fixed["questions"][0]["prompt"]
    assert "Caf\u00e9 zero R\u00e4ikk\u00f6nen \u2014 AT&T <vector>" in prompt


def test_question_bank_audit_and_fix_commands(tmp_path: Path):
    src = tmp_path / "bad.json"
    dest = tmp_path / "fixed.json"
    _write_json(src, _hostile_bank())

    assert question_bank.main(["audit-text", "--src", str(src)]) == 1
    assert question_bank.main(["fix-text", "--src", str(src), "--dest", str(dest), "-f"]) == 0
    assert question_bank.main(["audit-text", "--src", str(dest)]) == 0


def test_render_audit_and_exam_pdf_handle_literal_markup_chars(tmp_path: Path):
    src = tmp_path / "render.json"
    pdf = tmp_path / "exam.pdf"
    data = {
        "categories": ["programming"],
        "questions": [
            {
                "id": "programming_001",
                "category": "programming",
                "difficulty": "easy",
                "prompt": "Which C++ header has std::vector? <vector>, AT&T, 5 < 10, &Delta;S, I<sub>a</sub>",
                "choices": ["<array>", "<list>", "<vector>", "AT&T"],
                "answer": 2,
            }
        ],
    }
    _write_json(src, data)

    assert question_bank.main(["render-audit", "--src", str(src), "--target", "pdf"]) == 0
    create_exam.build_exam_pdf(data["questions"], pdf)
    assert pdf.exists()
    assert pdf.stat().st_size > 0


def test_flatten_questions_supports_pub_quiz_rounds():
    data = {"rounds": [{"title": "Round 1", "questions": [{"prompt": "Q1?"}, {"prompt": "Q2?"}]}]}
    assert json_tools.flatten_questions(data) == [{"prompt": "Q1?"}, {"prompt": "Q2?"}]


def test_ascii_only_flags_valid_specials(tmp_path: Path):
    src = tmp_path / "ascii.json"
    _write_json(src, {
        "questions": [
            {"prompt": "Caf\u00e9 0\u00b0C x\u00b2 9\u00be", "choices": ["A", "B", "C", "D"], "answer": 0}
        ]
    })

    issues = text_audit.audit_file(src, ascii_only=True)
    assert any(issue.code == "non_ascii" for issue in issues)


def test_markdown_to_html_escapes_raw_special_chars():
    html = html_md_convert.md_to_html("AT&T uses `<vector>` and 5 < 10.")
    assert "AT&amp;T" in html
    assert "<code>&lt;vector&gt;</code>" in html
    assert "5 &lt; 10" in html
