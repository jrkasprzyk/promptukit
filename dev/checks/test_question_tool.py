import json
from pathlib import Path

import promptukit.questions.question_bank as tt


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
