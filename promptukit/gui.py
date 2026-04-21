"""NiceGUI-based authoring GUI for promptukit question banks.

This module provides a lightweight browser GUI for authoring multiple-choice
question banks (prompt + 4 choices + answer index + category + difficulty,
with optional quips) — the same schema used by the rest of the package and
validated by ``promptukit.questions.validate_question``.

Launch from Python:

    from promptukit import launch_gui
    launch_gui()                           # default file in cwd
    launch_gui(file_path="my_bank.json")

Or from the shell after installing the package:

    promptukit-gui
    promptukit-gui -f my_bank.json

On-disk format matches the existing package convention:

    {
      "_schema_notes": [...],     # optional, preserved on round-trip
      "categories": [...],        # optional, declares allowed categories
      "questions": [
        {
          "id": "motorsport_001",
          "category": "motorsport",
          "difficulty": "easy",
          "prompt": "…",
          "choices": ["A", "B", "C", "D"],
          "answer": 0,
          "quip_correct": "…",    # optional
          "quip_wrong": "…"       # optional
        }
      ]
    }

Unknown top-level keys and unknown per-question keys are preserved verbatim on
save, so the GUI is safe to point at files with extra metadata it doesn't know
about.
"""

from __future__ import annotations

import json
import sys
from dataclasses import dataclass, field, asdict
from pathlib import Path
from typing import Any, Optional


DEFAULT_FILENAME = "promptukit_questions.json"

VALID_DIFFICULTIES = ("easy", "medium", "hard")
KNOWN_QUESTION_FIELDS = {
    "id",
    "category",
    "difficulty",
    "prompt",
    "choices",
    "answer",
    "quip_correct",
    "quip_wrong",
}


@dataclass
class Question:
    """A single multiple-choice question. Mirrors the schema validated by
    ``promptukit.questions.validate_question``."""

    id: str = ""
    category: str = ""
    difficulty: str = "easy"
    prompt: str = ""
    choices: list[str] = field(default_factory=lambda: ["", "", "", ""])
    answer: int = 0
    quip_correct: str = ""
    quip_wrong: str = ""
    # Any per-question keys we don't know about — preserved verbatim on save.
    extra: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict:
        d: dict[str, Any] = {
            "id": self.id,
            "category": self.category,
            "difficulty": self.difficulty,
            "prompt": self.prompt,
            "choices": list(self.choices),
            "answer": self.answer,
        }
        # Emit quip fields only when non-empty — the existing banks do this.
        if self.quip_correct:
            d["quip_correct"] = self.quip_correct
        if self.quip_wrong:
            d["quip_wrong"] = self.quip_wrong
        for k, v in self.extra.items():
            d.setdefault(k, v)
        return d

    @classmethod
    def from_dict(cls, d: dict) -> "Question":
        extra = {k: v for k, v in d.items() if k not in KNOWN_QUESTION_FIELDS}
        choices = d.get("choices")
        if not isinstance(choices, list):
            choices = ["", "", "", ""]
        else:
            choices = [str(c) for c in choices]
        answer = d.get("answer", 0)
        if not isinstance(answer, int):
            try:
                answer = int(answer)
            except (TypeError, ValueError):
                answer = 0
        return cls(
            id=str(d.get("id", "")),
            category=str(d.get("category", "")),
            difficulty=str(d.get("difficulty", "easy")),
            prompt=str(d.get("prompt", "")),
            choices=choices,
            answer=answer,
            quip_correct=str(d.get("quip_correct", "")),
            quip_wrong=str(d.get("quip_wrong", "")),
            extra=extra,
        )


class QuestionStore:
    """In-memory question bank tied to a JSON file on disk.

    Preserves unknown top-level keys (e.g. ``_schema_notes``) and unknown
    per-question keys so round-tripping through the GUI doesn't silently
    drop data the GUI doesn't know about.
    """

    def __init__(self, path: Path):
        self.path: Path = path
        self.questions: list[Question] = []
        self.categories: list[str] = []
        self.schema_notes: list[Any] = []
        # Unknown top-level keys preserved verbatim.
        self.extra: dict[str, Any] = {}
        self.selected_id: Optional[str] = None

    def load(self) -> None:
        if not self.path.exists():
            self.questions = []
            self.categories = []
            self.schema_notes = []
            self.extra = {}
            return
        with self.path.open("r", encoding="utf-8") as f:
            raw = json.load(f)
        if raw is None:
            self.questions = []
            self.categories = []
            self.schema_notes = []
            self.extra = {}
            return
        if not isinstance(raw, dict) or not isinstance(raw.get("questions"), list):
            raise ValueError(
                f"{self.path} must be an object with a top-level 'questions' list"
            )
        self.questions = [Question.from_dict(d) for d in raw["questions"]]
        cats = raw.get("categories")
        self.categories = [str(c) for c in cats] if isinstance(cats, list) else []
        notes = raw.get("_schema_notes")
        self.schema_notes = list(notes) if isinstance(notes, list) else []
        self.extra = {
            k: v for k, v in raw.items()
            if k not in {"questions", "categories", "_schema_notes"}
        }

    def save(self) -> None:
        payload: dict[str, Any] = {}
        if self.schema_notes:
            payload["_schema_notes"] = list(self.schema_notes)
        if self.categories:
            payload["categories"] = list(self.categories)
        for k, v in self.extra.items():
            payload.setdefault(k, v)
        payload["questions"] = [q.to_dict() for q in self.questions]
        with self.path.open("w", encoding="utf-8") as f:
            json.dump(payload, f, indent=2, ensure_ascii=False)

    def to_json(self, only: Optional[Question] = None) -> str:
        if only is not None:
            # Copy-selected emits just the single question dict, which is what
            # you'd paste into a bank's "questions" array.
            return json.dumps(only.to_dict(), indent=2, ensure_ascii=False)
        payload: dict[str, Any] = {}
        if self.schema_notes:
            payload["_schema_notes"] = list(self.schema_notes)
        if self.categories:
            payload["categories"] = list(self.categories)
        for k, v in self.extra.items():
            payload.setdefault(k, v)
        payload["questions"] = [q.to_dict() for q in self.questions]
        return json.dumps(payload, indent=2, ensure_ascii=False)

    def new(self) -> Question:
        q = Question(id=self._next_id())
        self.questions.append(q)
        self.selected_id = q.id
        return q

    def duplicate(self, q: Question) -> Question:
        copy = Question(
            id=self._next_id(base=q.category or "question"),
            category=q.category,
            difficulty=q.difficulty,
            prompt=q.prompt,
            choices=list(q.choices),
            answer=q.answer,
            quip_correct=q.quip_correct,
            quip_wrong=q.quip_wrong,
            extra=dict(q.extra),
        )
        idx = self._index_of(q.id)
        if idx is None:
            self.questions.append(copy)
        else:
            self.questions.insert(idx + 1, copy)
        self.selected_id = copy.id
        return copy

    def delete(self, q: Question) -> None:
        self.questions = [x for x in self.questions if x.id != q.id]
        if self.selected_id == q.id:
            self.selected_id = self.questions[0].id if self.questions else None

    def get(self, qid: str) -> Optional[Question]:
        for q in self.questions:
            if q.id == qid:
                return q
        return None

    def selected(self) -> Optional[Question]:
        if self.selected_id is None:
            return None
        return self.get(self.selected_id)

    def _index_of(self, qid: str) -> Optional[int]:
        for i, q in enumerate(self.questions):
            if q.id == qid:
                return i
        return None

    def _next_id(self, base: str = "question") -> str:
        """Generate a new id like ``<base>_NNN`` that doesn't collide with
        existing ids. Matches the convention in the shipped banks (e.g.
        ``motorsport_001``)."""
        base = (base or "question").strip().replace(" ", "_").lower() or "question"
        existing = {q.id for q in self.questions}
        n = 1
        while True:
            candidate = f"{base}_{n:03d}"
            if candidate not in existing:
                return candidate
            n += 1


def launch(file_path: Optional[Path] = None, port: int = 8080, show: bool = True) -> None:
    """Launch the NiceGUI authoring app.

    Args:
        file_path: JSON working file — loaded on startup (if it exists) and
            overwritten by "Save all to file". Defaults to
            ``./promptukit_questions.json`` in the current working directory.
        port: Port for the local web server.
        show: If True (default), automatically open a browser tab.
    """
    from nicegui import ui

    path = Path(file_path) if file_path is not None else Path.cwd() / DEFAULT_FILENAME
    store = QuestionStore(path)
    store.load()

    dirty = {"value": False}

    @ui.page("/")
    def main_page() -> None:
        ui.page_title("promptukit")

        # ---- Top bar ------------------------------------------------------
        with ui.row().classes("w-full items-center gap-2 p-2 bg-slate-100"):
            ui.label("promptukit").classes("text-lg font-bold")
            path_label = ui.label(f"Working file: {store.path}").classes("text-sm text-slate-600")
            ui.space()
            ui.button("Open…", on_click=lambda: open_dialog()).props("flat")
            ui.button("Reload from file", on_click=lambda: reload_file()).props("flat")
            ui.button("Save all to file", on_click=lambda: save_all()).props("color=primary")
            ui.button("Save as…", on_click=lambda: save_as_dialog()).props("flat")
            ui.button("Copy all as JSON", on_click=lambda: copy_json(all_=True))
            ui.button("Copy selected as JSON", on_click=lambda: copy_json(all_=False))

        # ---- Resizable two-pane body --------------------------------------
        splitter = ui.splitter(value=33).classes("w-full").style("height: calc(100vh - 64px)")
        with splitter.before:
            with ui.column().classes("w-full h-full gap-2 p-2"):
                ui.button("+ New", on_click=lambda: create_new()).props("color=primary").classes("w-full")
                list_container = ui.column().classes("w-full gap-1 overflow-auto").style(
                    "max-height: calc(100vh - 120px)"
                )
        with splitter.after:
            with ui.column().classes("w-full h-full gap-2 p-2 overflow-auto"):
                editor_container = ui.column().classes("w-full gap-2")

        # ---- Editor widget refs -------------------------------------------
        widgets: dict[str, Any] = {}

        def mark_dirty() -> None:
            dirty["value"] = True

        # ---- List rendering -----------------------------------------------
        def render_list() -> None:
            list_container.clear()
            with list_container:
                if not store.questions:
                    ui.label("No questions yet. Click + New to start.").classes(
                        "text-slate-500 italic p-2"
                    )
                    return
                for q in store.questions:
                    selected = q.id == store.selected_id
                    row_classes = "w-full p-2 rounded cursor-pointer border"
                    row_classes += (
                        " bg-blue-100 border-blue-400"
                        if selected
                        else " bg-white hover:bg-slate-50"
                    )
                    with ui.element("div").classes(row_classes).on(
                        "click", lambda _e, qid=q.id: attempt_select(qid)
                    ):
                        ui.label(q.prompt or "(empty prompt)").classes(
                            "font-medium"
                        ).style("white-space: normal; word-break: break-word;")
                        with ui.row().classes("gap-1 mt-1 items-center"):
                            ui.label(q.id or "(no id)").classes("text-xs text-slate-500")
                            if q.category:
                                ui.badge(q.category).props("color=blue-2 text-color=black")
                            if q.difficulty:
                                color = {
                                    "easy": "green-3",
                                    "medium": "amber-3",
                                    "hard": "red-3",
                                }.get(q.difficulty, "grey-4")
                                ui.badge(q.difficulty).props(f"color={color} text-color=black")

        # ---- Editor rendering ---------------------------------------------
        def render_editor() -> None:
            editor_container.clear()
            widgets.clear()
            q = store.selected()
            with editor_container:
                if q is None:
                    ui.label("Select a question on the left, or click + New.").classes(
                        "text-slate-500 italic"
                    )
                    return

                # ID + category + difficulty on one row
                with ui.row().classes("w-full gap-2 items-end no-wrap"):
                    widgets["id"] = ui.input(label="ID", value=q.id).classes("flex-1")
                    widgets["id"].on("update:model-value", lambda _e: mark_dirty())

                    # Category — free text, but show known categories as autocomplete.
                    widgets["category"] = ui.input(
                        label="Category",
                        value=q.category,
                        autocomplete=store.categories or None,
                    ).classes("flex-1")
                    widgets["category"].on("update:model-value", lambda _e: mark_dirty())

                    widgets["difficulty"] = ui.select(
                        options=list(VALID_DIFFICULTIES),
                        label="Difficulty",
                        value=q.difficulty if q.difficulty in VALID_DIFFICULTIES else "easy",
                    ).classes("w-40")
                    widgets["difficulty"].on("update:model-value", lambda _e: mark_dirty())

                widgets["prompt"] = ui.textarea(label="Prompt", value=q.prompt).props(
                    "autogrow"
                ).classes("w-full")
                widgets["prompt"].on("update:model-value", lambda _e: mark_dirty())

                # ---- Choices + answer radio ---------------------------------
                ui.label("Choices (select the radio next to the correct answer)").classes(
                    "text-sm text-slate-600 mt-2"
                )
                # Normalize to exactly 4 choices for the editor UI.
                initial_choices = list(q.choices) + [""] * max(0, 4 - len(q.choices))
                initial_choices = initial_choices[:4]
                answer_value = q.answer if 0 <= q.answer < 4 else 0
                widgets["answer"] = {"value": answer_value}
                widgets["choices"] = []

                def make_answer_setter(idx: int):
                    def _set(_e=None):
                        widgets["answer"]["value"] = idx
                        mark_dirty()
                    return _set

                labels = ["A", "B", "C", "D"]
                for i, text in enumerate(initial_choices):
                    with ui.row().classes("w-full items-center gap-2 no-wrap"):
                        radio = ui.radio(
                            {i: labels[i]},
                            value=i if answer_value == i else None,
                        ).props("dense inline").on(
                            "update:model-value", make_answer_setter(i)
                        )
                        widgets.setdefault("answer_radios", []).append(radio)
                        choice_input = ui.input(value=text).classes("flex-1")
                        choice_input.on("update:model-value", lambda _e: mark_dirty())
                        widgets["choices"].append(choice_input)

                widgets["quip_correct"] = ui.textarea(
                    label="Quip (correct) — optional",
                    value=q.quip_correct,
                ).props("autogrow").classes("w-full")
                widgets["quip_correct"].on("update:model-value", lambda _e: mark_dirty())

                widgets["quip_wrong"] = ui.textarea(
                    label="Quip (wrong) — optional",
                    value=q.quip_wrong,
                ).props("autogrow").classes("w-full")
                widgets["quip_wrong"].on("update:model-value", lambda _e: mark_dirty())

                with ui.row().classes("gap-2 mt-2"):
                    ui.button("Apply", on_click=lambda: apply_editor()).props("color=primary")
                    ui.button("Duplicate", on_click=lambda: duplicate_selected())
                    ui.button("Delete", on_click=lambda: confirm_delete()).props("color=negative")

        # ---- Commit editor -> store ---------------------------------------
        def commit_editor_to_store() -> None:
            q = store.selected()
            if q is None or not widgets:
                return
            q.id = (widgets["id"].value or "").strip()
            q.category = (widgets["category"].value or "").strip()
            q.difficulty = widgets["difficulty"].value or "easy"
            q.prompt = widgets["prompt"].value or ""
            q.choices = [(c.value or "") for c in widgets["choices"]]
            q.answer = int(widgets["answer"]["value"])
            q.quip_correct = widgets["quip_correct"].value or ""
            q.quip_wrong = widgets["quip_wrong"].value or ""
            # Keep radio buttons visually in sync (only the selected one stays lit).
            for i, radio in enumerate(widgets.get("answer_radios", [])):
                radio.value = i if i == q.answer else None

        def apply_editor() -> None:
            commit_editor_to_store()
            dirty["value"] = False
            render_list()
            ui.notify(
                "Applied edits to in-memory list. Use 'Save all to file' to persist.",
                type="positive",
            )

        # ---- Navigation / lifecycle actions -------------------------------
        def create_new() -> None:
            def do():
                store.new()
                dirty["value"] = False
                render_list()
                render_editor()
            if dirty["value"]:
                prompt_unsaved(do)
            else:
                do()

        def attempt_select(qid: str) -> None:
            if qid == store.selected_id:
                return
            def do():
                store.selected_id = qid
                dirty["value"] = False
                render_list()
                render_editor()
            if dirty["value"]:
                prompt_unsaved(do)
            else:
                do()

        def duplicate_selected() -> None:
            commit_editor_to_store()
            q = store.selected()
            if q is None:
                return
            store.duplicate(q)
            dirty["value"] = False
            render_list()
            render_editor()

        def confirm_delete() -> None:
            q = store.selected()
            if q is None:
                return
            with ui.dialog() as dialog, ui.card():
                ui.label("Delete this question? This cannot be undone.")
                ui.label(q.prompt or "(empty)").classes("italic text-slate-600").style(
                    "white-space: normal; word-break: break-word;"
                )
                with ui.row():
                    ui.button("Cancel", on_click=dialog.close).props("flat")
                    def do_delete():
                        store.delete(q)
                        dirty["value"] = False
                        dialog.close()
                        render_list()
                        render_editor()
                    ui.button("Delete", on_click=do_delete).props("color=negative")
            dialog.open()

        def prompt_unsaved(then) -> None:
            with ui.dialog() as dialog, ui.card():
                ui.label("You have unsaved edits in the editor.")
                ui.label("Discard them and continue?")
                with ui.row():
                    ui.button("Cancel", on_click=dialog.close).props("flat")
                    def do():
                        dialog.close()
                        then()
                    ui.button("Discard & continue", on_click=do).props("color=negative")
            dialog.open()

        def save_all() -> None:
            commit_editor_to_store()
            try:
                store.save()
                ui.notify(
                    f"Wrote {len(store.questions)} question(s) to {store.path}",
                    type="positive",
                )
            except Exception as e:
                ui.notify(f"Failed to save: {e}", type="negative")

        def save_as_dialog() -> None:
            commit_editor_to_store()
            with ui.dialog() as dialog, ui.card().classes("w-[40rem]"):
                ui.label("Save a copy as…").classes("text-lg font-bold")
                ui.label(
                    "Write the current in-memory bank to a new path and switch the "
                    "working file to it. The previous working file is not modified."
                ).classes("text-sm text-slate-600")
                suggested = str(store.path.with_name(store.path.stem + "_copy" + store.path.suffix))
                path_input = ui.input(label="New file path", value=suggested).classes("w-full")
                overwrite = ui.checkbox("Overwrite if the file already exists", value=False)
                with ui.row():
                    ui.button("Cancel", on_click=dialog.close).props("flat")
                    def do_save_as():
                        new_path = Path(path_input.value).expanduser()
                        if new_path.exists() and not overwrite.value:
                            ui.notify(
                                f"{new_path} already exists. Tick 'Overwrite' to replace it.",
                                type="warning",
                            )
                            return
                        try:
                            previous = store.path
                            store.path = new_path
                            store.save()
                            dirty["value"] = False
                            dialog.close()
                            path_label.set_text(f"Working file: {store.path}")
                            ui.notify(
                                f"Wrote {len(store.questions)} question(s) to {new_path}. "
                                f"Working file switched from {previous}.",
                                type="positive",
                            )
                        except Exception as e:
                            ui.notify(f"Failed to save: {e}", type="negative")
                    ui.button("Save as", on_click=do_save_as).props("color=primary")
            dialog.open()

        def reload_file() -> None:
            def do():
                try:
                    store.load()
                    store.selected_id = store.questions[0].id if store.questions else None
                    dirty["value"] = False
                    render_list()
                    render_editor()
                    ui.notify(f"Reloaded from {store.path}", type="positive")
                except Exception as e:
                    ui.notify(f"Failed to reload: {e}", type="negative")
            if dirty["value"]:
                prompt_unsaved(do)
            else:
                do()

        def open_dialog() -> None:
            def build():
                with ui.dialog() as dialog, ui.card().classes("w-[40rem]"):
                    ui.label("Open a JSON working file").classes("text-lg font-bold")
                    ui.label(
                        "Enter a path to an existing file (it will be loaded) or a new "
                        "path (an empty file will be created on the next 'Save all to file')."
                    ).classes("text-sm text-slate-600")
                    path_input = ui.input(label="File path", value=str(store.path)).classes("w-full")
                    with ui.row():
                        ui.button("Cancel", on_click=dialog.close).props("flat")
                        def do_open():
                            new_path = Path(path_input.value).expanduser()
                            try:
                                store.path = new_path
                                store.load()
                                store.selected_id = (
                                    store.questions[0].id if store.questions else None
                                )
                                dirty["value"] = False
                                dialog.close()
                                path_label.set_text(f"Working file: {store.path}")
                                render_list()
                                render_editor()
                                if new_path.exists():
                                    ui.notify(f"Loaded {new_path}", type="positive")
                                else:
                                    ui.notify(
                                        f"{new_path} does not exist yet — starting empty. "
                                        f"It will be created on 'Save all to file'.",
                                        type="info",
                                    )
                            except Exception as e:
                                ui.notify(f"Failed to open: {e}", type="negative")
                        ui.button("Open", on_click=do_open).props("color=primary")
                dialog.open()
            if dirty["value"]:
                prompt_unsaved(build)
            else:
                build()

        def copy_json(all_: bool) -> None:
            if all_:
                commit_editor_to_store()
                text = store.to_json()
                label = f"{len(store.questions)} question(s)"
            else:
                q = store.selected()
                if q is None:
                    ui.notify("No question selected.", type="warning")
                    return
                commit_editor_to_store()
                text = store.to_json(only=store.selected())
                label = "selected question"
            js_literal = json.dumps(text)
            ui.run_javascript(f"navigator.clipboard.writeText({js_literal})")
            ui.notify(f"Copied {label} to clipboard.", type="positive")

        # ---- Initial render ----------------------------------------------
        if store.selected_id is None and store.questions:
            store.selected_id = store.questions[0].id
        render_list()
        render_editor()

    print(f"promptukit GUI running at http://localhost:{port}", file=sys.stderr)
    ui.run(port=port, reload=False, show=show, title="promptukit")


def main() -> None:
    """Console-script entry point."""
    import argparse

    parser = argparse.ArgumentParser(
        description=(
            "Launch the promptukit authoring GUI. The file you pass is the "
            "working document: it's loaded on startup (if it exists) and "
            "overwritten when you click 'Save all to file' in the GUI."
        ),
    )
    parser.add_argument(
        "-f",
        "--file",
        dest="file",
        type=Path,
        default=None,
        help=f"JSON working file to load and save (default: ./{DEFAULT_FILENAME})",
    )
    parser.add_argument("-p", "--port", type=int, default=8080, help="Port (default: 8080)")
    parser.add_argument(
        "--no-browser",
        action="store_true",
        help="Don't automatically open a browser tab.",
    )
    args = parser.parse_args()
    launch(file_path=args.file, port=args.port, show=not args.no_browser)


if __name__ in {"__main__", "__mp_main__"}:
    main()
