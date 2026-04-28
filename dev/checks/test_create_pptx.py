from importlib import resources
from pathlib import Path

import pytest
from pptx import Presentation

from promptukit.exams import create_pptx


@pytest.fixture
def mixed_bank_path() -> Path:
    return Path(resources.files("promptukit").joinpath("data/question_banks/mixed-types-sample.json"))


@pytest.fixture
def pub_quiz_bank_path() -> Path:
    return Path(resources.files("promptukit").joinpath("data/question_banks/pub-quiz-sample.json"))


def _slide_count(path: Path) -> int:
    return len(list(Presentation(str(path)).slides))


def test_invalid_answer_mode_raises(tmp_path, mixed_bank_path):
    bank = create_pptx._read_question_bank(str(mixed_bank_path))
    with pytest.raises(ValueError):
        create_pptx.build_pptx(bank, tmp_path / "x.pptx", answers="bogus")


@pytest.mark.parametrize("mode,expected_factor", [("none", 1), ("inline", 1), ("after", 2)])
def test_build_pptx_mixed_types(tmp_path, mixed_bank_path, mode, expected_factor):
    bank = create_pptx._read_question_bank(str(mixed_bank_path))
    n_questions = len(create_pptx._flatten_questions(bank))
    assert n_questions == 6, "fixture should expose all 6 question types"

    out = tmp_path / f"deck_{mode}.pptx"
    create_pptx.build_pptx(bank, out, answers=mode)

    assert out.exists()
    expected = 1 + n_questions * expected_factor  # cover + question slides (+ answers)
    assert _slide_count(out) == expected


def test_build_pptx_rounds_format(tmp_path, pub_quiz_bank_path):
    bank = create_pptx._read_question_bank(str(pub_quiz_bank_path))
    n_questions = len(create_pptx._flatten_questions(bank))
    assert n_questions > 0

    out = tmp_path / "trivia.pptx"
    create_pptx.build_pptx(bank, out, answers="after")
    assert _slide_count(out) == 1 + n_questions * 2


def test_pptx_safe_text_strips_markup_and_resolves_entities():
    raw = "I<sub>a</sub> = 0.2S &mdash; &Delta;P"
    out = create_pptx.pptx_safe_text(raw)
    assert "<" not in out and ">" not in out
    assert "—" in out
    assert "Δ" in out


def test_cli_main_writes_file(tmp_path, mixed_bank_path):
    out = tmp_path / "cli.pptx"
    rc = create_pptx.main(["-q", str(mixed_bank_path), "-o", str(out), "--answers", "after"])
    assert rc == 0
    assert out.exists()
    assert _slide_count(out) == 13  # 1 cover + 6 questions * 2
