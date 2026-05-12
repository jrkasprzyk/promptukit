"""Tests for new features: Code question type, stimulus fields,
answer_space, Gradescope choice markers, answer key, and LaTeX support.
"""
import json
from pathlib import Path

import pytest

import promptukit.utils.json_tools as jt
from promptukit.exams import create_exam
from promptukit.questions.question_models import (
    Calculation,
    Code,
    FillInTheBlank,
    Matching,
    MultipleChoice,
    Question,
    ShortAnswer,
    TrueFalse,
)
from promptukit.questions import validate_question


# ---------------------------------------------------------------------------
# Code question type
# ---------------------------------------------------------------------------

def test_code_construction_and_serialization():
    c = Code(text="What does this print?", code="print('hello')", language="python", answer="hello")
    assert c.question_type == "Code"
    assert c.code == "print('hello')"
    assert c.language == "python"
    assert c.answer == "hello"
    d = c.to_dict()
    assert d["question_type"] == "Code"
    assert d["code"] == "print('hello')"
    assert d["language"] == "python"
    assert d["answer"] == "hello"


def test_code_from_json():
    obj = Question.from_json({
        "question_type": "Code",
        "prompt": "What is the output?",
        "code": "x = 1 + 1\nprint(x)",
        "language": "python",
        "answer": "2",
    })
    assert isinstance(obj, Code)
    assert obj.code == "x = 1 + 1\nprint(x)"
    assert obj.language == "python"
    assert obj.answer == "2"


def test_code_from_json_minimal():
    """Code question without optional fields."""
    obj = Code.from_json({"prompt": "Trace this.", "code": "x = 42"})
    assert isinstance(obj, Code)
    assert obj.code == "x = 42"
    assert obj.language == ""
    assert obj.answer == ""


def test_code_round_trip():
    c = Code(text="Output?", code="print(1)", language="python", answer="1")
    d = c.to_dict()
    restored = Question.from_json(d)
    assert isinstance(restored, Code)
    assert restored.code == c.code


def test_code_infer_from_keys():
    """infer_question_type detects 'code' field."""
    assert jt.infer_question_type({"code": "print(1)"}) == "Code"


def test_code_preserve_raw():
    raw = {"question_type": "Code", "prompt": "Q?", "code": "x=1", "extra_field": "keep"}
    c = Code.from_json(raw)
    out = c.to_dict(preserve_raw=True)
    assert out["extra_field"] == "keep"
    assert out["question_type"] == "Code"


# ---------------------------------------------------------------------------
# Stimulus fields
# ---------------------------------------------------------------------------

def test_stimulus_on_base_question():
    q = Question(text="Refer to the table.", has_stimulus=True, stimulus_location="fig1.png")
    assert q.has_stimulus is True
    assert q.stimulus_location == "fig1.png"
    d = q.to_dict()
    assert d["has_stimulus"] is True
    assert d["stimulus_location"] == "fig1.png"


def test_stimulus_on_multiple_choice():
    mc = MultipleChoice(
        text="Which item?", choices=["A", "B", "C", "D"], answer=0,
        has_stimulus=True, stimulus_location="https://example.com/table.png",
    )
    d = mc.to_dict()
    assert d["has_stimulus"] is True
    assert d["stimulus_location"] == "https://example.com/table.png"


def test_stimulus_from_json_all_types():
    """All concrete types parse stimulus fields from JSON."""
    stimulus_data = {"has_stimulus": True, "stimulus_location": "img.png"}
    base_mc = {"question_type": "MultipleChoice", "prompt": "Q?", "choices": ["A", "B"], "answer": 0}
    mc = MultipleChoice.from_json({**base_mc, **stimulus_data})
    assert mc.has_stimulus is True
    assert mc.stimulus_location == "img.png"

    tf = TrueFalse.from_json({"prompt": "T?", "answer": True, **stimulus_data})
    assert tf.has_stimulus is True

    sa = ShortAnswer.from_json({"prompt": "S?", "answer": "x", **stimulus_data})
    assert sa.has_stimulus is True

    fitb = FillInTheBlank.from_json({"prompt": "[blank]", "answers": ["x"], **stimulus_data})
    assert fitb.has_stimulus is True

    m = Matching.from_json({"prompt": "M?", "pairs": [["A", "1"]], **stimulus_data})
    assert m.has_stimulus is True

    calc = Calculation.from_json({"prompt": "C?", "answer": 1.0, **stimulus_data})
    assert calc.has_stimulus is True

    code = Code.from_json({"prompt": "Code?", "code": "x=1", **stimulus_data})
    assert code.has_stimulus is True


def test_no_stimulus_no_extra_fields():
    """Stimulus fields are omitted when false/empty."""
    mc = MultipleChoice(text="Q?", choices=["A", "B"], answer=0)
    d = mc.to_dict()
    assert "has_stimulus" not in d
    assert "stimulus_location" not in d


# ---------------------------------------------------------------------------
# answer_space field
# ---------------------------------------------------------------------------

def test_short_answer_answer_space_string():
    sa = ShortAnswer(text="Explain.", answer="because", answer_space="large")
    d = sa.to_dict()
    assert d["answer_space"] == "large"


def test_short_answer_answer_space_numeric():
    sa = ShortAnswer(text="Q?", answer="a", answer_space=3.0)
    d = sa.to_dict()
    assert d["answer_space"] == 3.0


def test_short_answer_answer_space_from_json():
    obj = ShortAnswer.from_json({"prompt": "Q?", "answer": "x", "answer_space": "small"})
    assert obj.answer_space == "small"


def test_calculation_answer_space():
    calc = Calculation(text="Solve.", answer=42.0, answer_space="medium")
    d = calc.to_dict()
    assert d["answer_space"] == "medium"


def test_calculation_answer_space_from_json():
    obj = Calculation.from_json({"prompt": "?", "answer": 1.0, "answer_space": 2.5})
    assert obj.answer_space == 2.5


def test_answer_space_omitted_when_none():
    sa = ShortAnswer(text="Q?", answer="a")
    d = sa.to_dict()
    assert "answer_space" not in d


# ---------------------------------------------------------------------------
# answer_space validation
# ---------------------------------------------------------------------------

def test_validate_answer_space_valid():
    for space in ("small", "medium", "large", 1.0, 2):
        q = {
            "id": "x_001", "category": "general", "difficulty": "easy",
            "prompt": "Q?", "answer": "yes", "question_type": "ShortAnswer",
            "answer_space": space,
        }
        errors, _ = validate_question.validate({"categories": ["general"], "questions": [q]})
        assert not errors, f"Unexpected errors for answer_space={space!r}: {errors}"


def test_validate_answer_space_invalid_string():
    q = {
        "id": "x_001", "category": "general", "difficulty": "easy",
        "prompt": "Q?", "answer": "yes", "question_type": "ShortAnswer",
        "answer_space": "huge",
    }
    errors, _ = validate_question.validate({"categories": ["general"], "questions": [q]})
    assert any("answer_space" in e for e in errors)


def test_validate_answer_space_invalid_zero():
    q = {
        "id": "x_001", "category": "general", "difficulty": "easy",
        "prompt": "Q?", "answer": "yes", "question_type": "ShortAnswer",
        "answer_space": 0,
    }
    errors, _ = validate_question.validate({"categories": ["general"], "questions": [q]})
    assert any("answer_space" in e for e in errors)


# ---------------------------------------------------------------------------
# Code question validation
# ---------------------------------------------------------------------------

def test_validate_code_question_valid():
    q = {
        "id": "prog_001", "category": "prog", "difficulty": "easy",
        "prompt": "What is the output?", "question_type": "Code",
        "code": "print(1 + 1)",
        "language": "python",
        "answer": "2",
    }
    errors, _ = validate_question.validate({"categories": ["prog"], "questions": [q]})
    assert not errors, errors


def test_validate_code_question_missing_code():
    q = {
        "id": "prog_001", "category": "prog", "difficulty": "easy",
        "prompt": "Q?", "question_type": "Code",
    }
    errors, _ = validate_question.validate({"categories": ["prog"], "questions": [q]})
    assert any("code" in e for e in errors)


def test_validate_code_question_empty_code():
    q = {
        "id": "prog_001", "category": "prog", "difficulty": "easy",
        "prompt": "Q?", "question_type": "Code", "code": "   ",
    }
    errors, _ = validate_question.validate({"categories": ["prog"], "questions": [q]})
    assert any("code" in e for e in errors)


# ---------------------------------------------------------------------------
# LaTeX conversion
# ---------------------------------------------------------------------------

def test_latex_to_reportlab_greek():
    result = create_exam.latex_to_reportlab("The value of $\\alpha + \\beta$ is small.")
    assert "α" in result
    assert "β" in result
    assert "$" not in result


def test_latex_to_reportlab_fraction():
    result = create_exam.latex_to_reportlab("Compute $\\frac{1}{2}$.")
    assert "(1)/(2)" in result
    assert "$" not in result


def test_latex_to_reportlab_sqrt():
    result = create_exam.latex_to_reportlab("Find $\\sqrt{x^2}$.")
    assert "√" in result
    assert "$" not in result


def test_latex_to_reportlab_superscript():
    result = create_exam.latex_to_reportlab("Area = $\\pi r^2$.")
    assert "π" in result
    assert "²" in result


def test_latex_to_reportlab_no_latex():
    text = "No math here."
    assert create_exam.latex_to_reportlab(text) == text


def test_latex_to_reportlab_backslash_paren():
    result = create_exam.latex_to_reportlab(r"Solve \(x + y = z\).")
    assert "$" not in result
    assert "\\(" not in result


# ---------------------------------------------------------------------------
# Gradescope-style choice markers
# ---------------------------------------------------------------------------

def test_choice_label_letter():
    fn = create_exam._get_choice_label_fn({"choice_marker": "letter"})
    assert fn(0) == "A) "
    assert fn(1) == "B) "


def test_choice_label_circle():
    fn = create_exam._get_choice_label_fn({"choice_marker": "circle"})
    assert fn(0).startswith("○")
    assert "A" in fn(0)


def test_choice_label_square():
    fn = create_exam._get_choice_label_fn({"choice_marker": "square"})
    assert fn(0).startswith("□")
    assert "A" in fn(0)


def test_choice_label_default_is_letter():
    fn = create_exam._get_choice_label_fn({})
    assert fn(0) == "A) "


# ---------------------------------------------------------------------------
# answer_space PDF spacer conversion
# ---------------------------------------------------------------------------

def test_answer_space_inches_strings():
    assert create_exam._answer_space_inches("small") == 1.0
    assert create_exam._answer_space_inches("medium") == 2.0
    assert create_exam._answer_space_inches("large") == 4.0


def test_answer_space_inches_numeric():
    assert create_exam._answer_space_inches(3.5) == 3.5
    assert create_exam._answer_space_inches(0) == 0.25  # clamped to minimum


def test_answer_space_inches_none():
    assert create_exam._answer_space_inches(None) == 2.0


# ---------------------------------------------------------------------------
# Answer key PDF generation
# ---------------------------------------------------------------------------

def _sample_mixed_questions():
    return [
        {
            "id": "q1", "category": "math", "difficulty": "easy",
            "prompt": "Pick one.", "question_type": "MultipleChoice",
            "choices": ["Paris", "London", "Berlin", "Madrid"], "answer": 0,
        },
        {
            "id": "q2", "category": "math", "difficulty": "easy",
            "prompt": "True or false?", "question_type": "TrueFalse",
            "answer": True,
        },
        {
            "id": "q3", "category": "math", "difficulty": "medium",
            "prompt": "Name the capital.", "question_type": "ShortAnswer",
            "answer": "Paris",
        },
        {
            "id": "q4", "category": "math", "difficulty": "hard",
            "prompt": "Area of r=3?", "question_type": "Calculation",
            "answer": 28.27, "tolerance": 0.05, "unit": "m^2",
        },
        {
            "id": "q5", "category": "prog", "difficulty": "easy",
            "prompt": "Output?", "question_type": "Code",
            "code": "print(2+2)", "language": "python", "answer": "4",
        },
    ]


def test_build_answer_key_pdf(tmp_path: Path):
    out = tmp_path / "key.pdf"
    create_exam.build_answer_key_pdf(
        {"questions": _sample_mixed_questions()},
        out,
        metadata={"title": "Test Exam"},
    )
    assert out.exists()
    assert out.stat().st_size > 0


def test_build_answer_key_with_sections(tmp_path: Path):
    sections = [{"title": "Section 1", "questions": _sample_mixed_questions()[:2]}]
    out = tmp_path / "key_sec.pdf"
    create_exam.build_answer_key_pdf(sections, out)
    assert out.exists()
    assert out.stat().st_size > 0


# ---------------------------------------------------------------------------
# Exam PDF with new features
# ---------------------------------------------------------------------------

def test_build_exam_pdf_with_code_question(tmp_path: Path):
    questions = [
        {
            "prompt": "What does this print?",
            "question_type": "Code",
            "code": "x = [1, 2, 3]\nprint(len(x))",
            "language": "python",
        }
    ]
    out = tmp_path / "exam_code.pdf"
    create_exam.build_exam_pdf({"questions": questions}, out)
    assert out.exists()


def test_build_exam_pdf_with_stimulus(tmp_path: Path):
    questions = [
        {
            "prompt": "Refer to the graph. Which trend is shown?",
            "question_type": "MultipleChoice",
            "choices": ["Increasing", "Decreasing", "Constant", "Cyclic"],
            "answer": 0,
            "has_stimulus": True,
            "stimulus_location": "figures/graph1.png",
        }
    ]
    out = tmp_path / "exam_stim.pdf"
    create_exam.build_exam_pdf({"questions": questions}, out)
    assert out.exists()


def test_build_exam_pdf_circle_markers(tmp_path: Path):
    questions = [
        {
            "prompt": "Pick one.",
            "question_type": "MultipleChoice",
            "choices": ["A", "B", "C", "D"],
            "answer": 0,
        }
    ]
    out = tmp_path / "exam_circle.pdf"
    create_exam.build_exam_pdf({"questions": questions}, out, metadata={"choice_marker": "circle"})
    assert out.exists()


def test_build_exam_pdf_square_markers(tmp_path: Path):
    questions = [
        {
            "prompt": "Pick one.",
            "question_type": "MultipleChoice",
            "choices": ["A", "B", "C", "D"],
            "answer": 0,
        }
    ]
    out = tmp_path / "exam_square.pdf"
    create_exam.build_exam_pdf({"questions": questions}, out, metadata={"choice_marker": "square"})
    assert out.exists()


def test_build_exam_pdf_answer_space_large(tmp_path: Path):
    questions = [
        {
            "prompt": "Explain in detail.",
            "question_type": "ShortAnswer",
            "answer": "...",
            "answer_space": "large",
        }
    ]
    out = tmp_path / "exam_space.pdf"
    create_exam.build_exam_pdf({"questions": questions}, out)
    assert out.exists()


def test_build_exam_pdf_latex_in_prompt(tmp_path: Path):
    questions = [
        {
            "prompt": "Evaluate $\\int_0^1 x^2 dx$ where $\\alpha = 1/3$.",
            "question_type": "ShortAnswer",
            "answer": "1/3",
        }
    ]
    out = tmp_path / "exam_latex.pdf"
    create_exam.build_exam_pdf({"questions": questions}, out)
    assert out.exists()


# ---------------------------------------------------------------------------
# add_question batch: Code type
# ---------------------------------------------------------------------------

def test_add_question_batch_code(tmp_path: Path):
    bank = tmp_path / "bank.json"
    import promptukit.questions.add_question as aq
    import tempfile, json

    batch = tmp_path / "batch.json"
    batch.write_text(json.dumps([{
        "question_type": "Code",
        "category": "prog",
        "difficulty": "easy",
        "prompt": "What is the output?",
        "code": "print(1 + 1)",
        "language": "python",
        "answer": "2",
    }]), encoding="utf-8")

    rc = aq.main(["--create", "--batch", str(batch), str(bank)])
    assert rc == 0
    data = json.loads(bank.read_text(encoding="utf-8"))
    q = data["questions"][0]
    assert q["question_type"] == "Code"
    assert q["code"] == "print(1 + 1)"
    assert q["language"] == "python"
