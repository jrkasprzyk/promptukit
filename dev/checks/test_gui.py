"""Smoke tests for promptukit.gui — does not start the NiceGUI server."""

from __future__ import annotations

import inspect
import json
from pathlib import Path


def test_module_imports():
    import promptukit.gui as gui  # noqa: F401


def test_launch_signature():
    from promptukit.gui import launch

    sig = inspect.signature(launch)
    params = sig.parameters
    assert "file_path" in params
    assert "port" in params
    assert "show" in params
    assert params["file_path"].default is None
    assert params["port"].default == 8080
    assert params["show"].default is True


def test_launch_gui_reexport():
    import promptukit

    assert hasattr(promptukit, "launch_gui")
    assert callable(promptukit.launch_gui)


def test_mcq_roundtrip(tmp_path: Path):
    """Write the full MCQ schema and make sure it survives a round-trip."""
    from promptukit.gui import Question, QuestionStore

    path = tmp_path / "bank.json"
    store = QuestionStore(path)
    store.categories = ["music", "motorsport"]
    store.schema_notes = ["Test bank — do not ship."]
    q = store.new()
    q.id = "music_001"
    q.category = "music"
    q.difficulty = "easy"
    q.prompt = "Which instrument has a keyboard and strings?"
    q.choices = ["Guitar", "Piano", "Violin", "Drums"]
    q.answer = 1
    q.quip_correct = "Yep."
    q.quip_wrong = "Nope."
    store.save()

    with path.open("r", encoding="utf-8") as f:
        raw = json.load(f)
    assert raw["categories"] == ["music", "motorsport"]
    assert raw["_schema_notes"] == ["Test bank — do not ship."]
    assert raw["questions"][0]["id"] == "music_001"
    assert raw["questions"][0]["answer"] == 1
    assert raw["questions"][0]["quip_correct"] == "Yep."

    store2 = QuestionStore(path)
    store2.load()
    assert store2.categories == ["music", "motorsport"]
    assert store2.schema_notes == ["Test bank — do not ship."]
    assert len(store2.questions) == 1
    loaded = store2.questions[0]
    assert loaded.id == "music_001"
    assert loaded.category == "music"
    assert loaded.difficulty == "easy"
    assert loaded.choices == ["Guitar", "Piano", "Violin", "Drums"]
    assert loaded.answer == 1


def test_unknown_fields_preserved(tmp_path: Path):
    """Unknown top-level keys and unknown per-question keys must survive a
    round-trip — the GUI is not allowed to silently drop them."""
    from promptukit.gui import QuestionStore

    path = tmp_path / "bank.json"
    original = {
        "categories": ["general"],
        "future_meta": {"owner": "alice"},
        "questions": [
            {
                "id": "g_001",
                "category": "general",
                "difficulty": "easy",
                "prompt": "2+2?",
                "choices": ["3", "4", "5", "6"],
                "answer": 1,
                "future_per_question_field": "keep me",
            }
        ],
    }
    with path.open("w", encoding="utf-8") as f:
        json.dump(original, f, indent=2)

    store = QuestionStore(path)
    store.load()
    store.save()

    with path.open("r", encoding="utf-8") as f:
        reloaded = json.load(f)
    assert reloaded["future_meta"] == {"owner": "alice"}
    assert reloaded["questions"][0]["future_per_question_field"] == "keep me"


def test_load_real_sample_bank(tmp_path: Path):
    """Sanity-check against a real shipped question bank."""
    import promptukit
    from promptukit.gui import QuestionStore

    pkg_root = Path(promptukit.__file__).parent
    sample = pkg_root / "data" / "question_banks" / "block-doku-sample.json"
    assert sample.exists(), "expected shipped sample bank to be present"

    # Copy it so the test doesn't write to the packaged file.
    target = tmp_path / "sample.json"
    target.write_text(sample.read_text(encoding="utf-8"), encoding="utf-8")

    store = QuestionStore(target)
    store.load()
    assert store.questions, "sample bank should load with questions"
    first = store.questions[0]
    assert first.id and first.prompt and first.choices
    assert 0 <= first.answer < 4

    # Round-trip should preserve the file's shape.
    store.save()
    with target.open("r", encoding="utf-8") as f:
        after = json.load(f)
    assert "questions" in after
    assert after["questions"][0]["id"] == first.id


def test_load_missing_file_is_empty(tmp_path: Path):
    from promptukit.gui import QuestionStore

    store = QuestionStore(tmp_path / "nope.json")
    store.load()
    assert store.questions == []
    assert store.categories == []


def test_next_id_avoids_collisions(tmp_path: Path):
    from promptukit.gui import QuestionStore

    store = QuestionStore(tmp_path / "x.json")
    a = store.new()
    a.category = "music"
    b = store.duplicate(a)
    assert a.id != b.id
