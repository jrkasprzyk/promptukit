import json
from pathlib import Path

import promptukit.questions.question_bank as tt
import promptukit.utils.json_tools as jt
from promptukit.questions.question_models import (
    MultipleChoice,
    TrueFalse,
    ShortAnswer,
    FillInTheBlank,
    Matching,
    Calculation,
    Question,
)


def _sample_questions():
    return [
        {
            "id": "music_001",
            "category": "music",
            "difficulty": "easy",
            "prompt": "Who wrote this song?",
            "choices": ["A", "B", "C", "D"],
            "answer": 0,
        },
        {
            "id": "film_001",
            "category": "film-and-tv",
            "difficulty": "easy",
            "prompt": "Which movie?",
            "choices": ["A", "B", "C", "D"],
            "answer": 1,
        },
        {
            "id": "music_002",
            "category": "music",
            "difficulty": "hard",
            "prompt": "Name the composer",
            "choices": ["A", "B", "C", "D"],
            "answer": 2,
        },
    ]


def test_filter_questions():
    qs = _sample_questions()
    out = tt.filter_questions(qs, categories=["music"])
    assert len(out) == 2

    out = tt.filter_questions(qs, difficulty="easy")
    assert len(out) == 2

    out = tt.filter_questions(qs, ids=["music_001"])
    assert len(out) == 1 and out[0]["id"] == "music_001"

    out = tt.filter_questions(qs, match="composer")
    assert len(out) == 1 and out[0]["id"] == "music_002"


def test_cmd_extract_and_create_and_copy(tmp_path: Path):
    # prepare source file
    src = tmp_path / "src.json"
    data = {"categories": ["music"], "questions": _sample_questions()}
    src.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")

    # extract
    dest = tmp_path / "out.json"
    rc = tt.main(["extract", "--src", str(src), "--dest", str(dest), "--categories", "music", "-f"])
    assert rc == 0
    assert dest.exists()
    out = json.loads(dest.read_text(encoding="utf-8"))
    assert "questions" in out and len(out["questions"]) >= 1

    # create
    newfile = tmp_path / "new.json"
    rc = tt.main(["create", "--dest", str(newfile), "--categories", "g1,g2", "-f"])
    assert rc == 0
    loaded = json.loads(newfile.read_text(encoding="utf-8"))
    assert loaded.get("categories") == ["g1", "g2"]

    # copy
    copyfile = tmp_path / "copy.json"
    rc = tt.main(["copy", "--src", str(newfile), "--dest", str(copyfile), "-f"])
    assert rc == 0
    assert json.loads(copyfile.read_text(encoding="utf-8")) == loaded


def test_json_tools_update_and_load(tmp_path: Path):
    src = tmp_path / "bank.json"
    data = {"categories": ["music"], "questions": [
        {"id": "q1", "prompt": "Sample?", "choices": ["A", "B"], "answer": 1}
    ]}
    src.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")

    # Add question_type tags in-place
    out = jt.update_json_file(src)
    assert out == src
    updated = json.loads(src.read_text(encoding="utf-8"))
    assert updated["questions"][0].get("question_type") == "MultipleChoice"

    # Load as objects
    objs = jt.load_questions_as_objects(src)
    assert len(objs) == 1
    assert isinstance(objs[0], MultipleChoice)
    assert objs[0].text == "Sample?"


# --- New question type tests ---

def test_true_false_construction_and_serialization():
    tf = TrueFalse(text="The sky is green.", answer=False)
    assert tf.question_type == "TrueFalse"
    assert tf.answer is False
    d = tf.to_dict()
    assert d["question_type"] == "TrueFalse"
    assert d["answer"] is False
    assert d["prompt"] == "The sky is green."


def test_true_false_from_json_bool():
    obj = Question.from_json({"question_type": "TrueFalse", "prompt": "2+2=4?", "answer": True})
    assert isinstance(obj, TrueFalse)
    assert obj.answer is True


def test_true_false_from_json_string():
    obj = TrueFalse.from_json({"prompt": "Water is wet?", "answer": "true"})
    assert obj.answer is True
    obj2 = TrueFalse.from_json({"prompt": "Fire is cold?", "answer": "false"})
    assert obj2.answer is False


def test_short_answer_construction_and_serialization():
    sa = ShortAnswer(text="What is the capital of France?", answer="Paris")
    assert sa.question_type == "ShortAnswer"
    d = sa.to_dict()
    assert d["answer"] == "Paris"
    assert d["question_type"] == "ShortAnswer"


def test_short_answer_from_json():
    obj = Question.from_json({"question_type": "ShortAnswer", "prompt": "Color of sky?", "answer": "blue"})
    assert isinstance(obj, ShortAnswer)
    assert obj.answer == "blue"


def test_fill_in_the_blank_construction_and_serialization():
    fitb = FillInTheBlank(text="___ is the powerhouse of the cell.", answers=["mitochondria"])
    assert fitb.question_type == "FillInTheBlank"
    d = fitb.to_dict()
    assert d["answers"] == ["mitochondria"]
    assert d["question_type"] == "FillInTheBlank"


def test_fill_in_the_blank_from_json():
    obj = Question.from_json({
        "question_type": "FillInTheBlank",
        "prompt": "___ and ___ are noble gases.",
        "answers": ["helium", "neon"],
    })
    assert isinstance(obj, FillInTheBlank)
    assert obj.answers == ["helium", "neon"]


def test_matching_construction_and_serialization():
    pairs = [["H", "Hydrogen"], ["O", "Oxygen"]]
    m = Matching(text="Match symbols to elements.", pairs=pairs)
    assert m.question_type == "Matching"
    d = m.to_dict()
    assert d["pairs"] == pairs
    assert d["question_type"] == "Matching"


def test_matching_from_json():
    obj = Question.from_json({
        "question_type": "Matching",
        "prompt": "Match capitals.",
        "pairs": [["France", "Paris"], ["Japan", "Tokyo"]],
    })
    assert isinstance(obj, Matching)
    assert len(obj.pairs) == 2
    assert obj.pairs[0] == ["France", "Paris"]


def test_calculation_construction_and_serialization():
    calc = Calculation(text="Speed?", answer=75.0, tolerance=0.5, unit="km/h")
    assert calc.question_type == "Calculation"
    d = calc.to_dict()
    assert d["answer"] == 75.0
    assert d["tolerance"] == 0.5
    assert d["unit"] == "km/h"


def test_calculation_is_correct():
    calc = Calculation(text="Q?", answer=100.0, tolerance=2.0)
    assert calc.is_correct(100.0)
    assert calc.is_correct(101.9)
    assert not calc.is_correct(102.1)


def test_calculation_from_json():
    obj = Question.from_json({
        "question_type": "Calculation",
        "prompt": "What is 6 * 7?",
        "answer": 42,
        "tolerance": 0,
    })
    assert isinstance(obj, Calculation)
    assert obj.answer == 42.0
    assert obj.is_correct(42)


def test_round_trip_all_types():
    objs = [
        MultipleChoice(text="MC?", choices=["A", "B", "C"], answer=0),
        TrueFalse(text="TF?", answer=True),
        ShortAnswer(text="SA?", answer="answer"),
        FillInTheBlank(text="___ blank.", answers=["fill"]),
        Matching(text="Match.", pairs=[["A", "1"], ["B", "2"]]),
        Calculation(text="Calc?", answer=9.81, tolerance=0.01, unit="m/s²"),
    ]
    for obj in objs:
        d = obj.to_dict()
        restored = Question.from_json(d)
        assert type(restored).__name__ == type(obj).__name__, f"Round-trip failed for {type(obj).__name__}"


def test_infer_question_type_new_types():
    assert jt.infer_question_type({"pairs": [["A", "1"]]}) == "Matching"
    assert jt.infer_question_type({"answers": ["x"]}) == "FillInTheBlank"
    assert jt.infer_question_type({"answer": True}) == "TrueFalse"
    assert jt.infer_question_type({"answer": 42}) == "Calculation"
    assert jt.infer_question_type({"answer": "Paris"}) == "ShortAnswer"
    assert jt.infer_question_type({"choices": ["A", "B"], "answer": 0}) == "MultipleChoice"


def test_multiple_choice_letter_answer():
    mc = MultipleChoice.from_json({"prompt": "Pick one.", "choices": ["Alpha", "Beta", "Gamma", "Delta"], "answer": "B"})
    assert mc.answer_index == 1
    assert mc.answer_text == "Beta"


def test_preserve_raw_survives_unknown_keys():
    raw = {"prompt": "Q?", "choices": ["A", "B"], "answer": 0, "custom_field": "keep_me", "question_type": "MultipleChoice"}
    mc = MultipleChoice.from_json(raw)
    out = mc.to_dict(preserve_raw=True)
    assert out["custom_field"] == "keep_me"
    assert out["question_type"] == "MultipleChoice"


def test_calculation_from_json_bad_answer():
    obj = Calculation.from_json({"prompt": "Speed?", "answer": "42 km/h"})
    assert obj.answer is None
    assert not obj.is_correct(42)
