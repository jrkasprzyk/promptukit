import json
from importlib import resources
from pathlib import Path

from promptukit.exams import create_exam_md


def _mixed_bank_path() -> Path:
    return Path(resources.files("promptukit").joinpath("data/question_banks/mixed-types-sample.json"))


def test_build_exam_md_student_facing_rendering(tmp_path):
    bank = create_exam_md._read_question_bank(str(_mixed_bank_path()))
    out = tmp_path / "exam.md"

    create_exam_md.build_exam_md(bank, out)

    text = out.read_text(encoding="utf-8")
    assert "Multiple Choice Examination" not in text
    assert f"{create_exam_md.CHOOSE_ONE_MARK} A) Paris" in text
    assert f"{create_exam_md.CHOOSE_ONE_MARK} True" in text
    assert f"The symbol for {create_exam_md.FILL_BLANK_LINE} is Au." in text
    assert "[blank]" not in text

    short_answer_block = text.split("Who wrote the Declaration of Independence?")[1]
    short_answer_block = short_answer_block.split("**5.**")[0]
    assert short_answer_block.count(create_exam_md.SHORT_ANSWER_LINE) == 2
    assert "*Answer:* _______________" not in text


def test_build_exam_md_prints_custom_exam_type(tmp_path):
    out = tmp_path / "exam.md"

    create_exam_md.build_exam_md(
        {"questions": []},
        out,
        metadata={"exam_type": "Hydrology Midterm"},
    )

    assert "*Hydrology Midterm*" in out.read_text(encoding="utf-8")


def test_build_exam_md_renders_choose_multiple_style_with_boxes(tmp_path):
    out = tmp_path / "exam.md"
    bank = {
        "questions": [
            {
                "question_type": "MultipleChoice",
                "prompt": "Select all vowels.",
                "choices": ["Alpha", "Beta", "Omega"],
                "answer": [0, 2],
            }
        ]
    }

    create_exam_md.build_exam_md(bank, out)

    text = out.read_text(encoding="utf-8")
    assert f"{create_exam_md.CHOOSE_MULTIPLE_MARK} A) Alpha" in text
    assert f"{create_exam_md.CHOOSE_MULTIPLE_MARK} C) Omega" in text


def test_cli_missing_question_file_prints_user_message(tmp_path, capsys):
    out = tmp_path / "exam.md"

    rc = create_exam_md.main(["-q", str(tmp_path / "missing.json"), "-o", str(out)])

    captured = capsys.readouterr()
    assert rc == 1
    assert "Question bank file not found" in captured.err
    assert str(tmp_path / "missing.json") in captured.err
    assert "Traceback" not in captured.err + captured.out
    assert not out.exists()


def test_cli_missing_metadata_file_prints_user_message(tmp_path, capsys):
    bank = tmp_path / "bank.json"
    bank.write_text(json.dumps({"questions": []}), encoding="utf-8")
    out = tmp_path / "exam.md"

    rc = create_exam_md.main([
        "-q",
        str(bank),
        "-m",
        str(tmp_path / "missing_setup.json"),
        "-o",
        str(out),
    ])

    captured = capsys.readouterr()
    assert rc == 1
    assert "Metadata file not found" in captured.err
    assert str(tmp_path / "missing_setup.json") in captured.err
    assert "Traceback" not in captured.err + captured.out
    assert not out.exists()
