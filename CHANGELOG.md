# Changelog

All notable changes to `promptukit` are documented here. The format follows
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/), and this project
adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html) (with
the understanding that during the `0.x` series, minor bumps may contain
breaking changes).

## [Unreleased]

### Removed
- `create_exam_md` module and `create-exam-md` CLI entry point — markdown rendering was unreliable and the pandoc conversion workflow did not function correctly in real-world testing; `create_exam` (ReportLab PDF) is the supported output path

### Fixed
- `create_exam` (`build_exam_pdf`) now renders all question types correctly:
  - `TrueFalse` — renders A) True / B) False choices
  - `ShortAnswer` — renders blank vertical space for handwriting
  - `FillInTheBlank` — replaces `[blank]` tokens with underscore lines
  - `Matching` — renders a two-column table with answer blanks
  - `Calculation` — renders an answer line with optional unit
- `load_questions_from_json` now preserves all original question fields (previously stripped everything except `q`, `choices`, `category`, discarding `question_type`, `answer`, `pairs`, etc.)
- Choice label detection regex tightened (`[\)\.]\s*` instead of `[\)\.\s]+`) — choices starting with a word like "X dominates…" or "Y dominates…" no longer treated as pre-labeled

### Changed
- Question spacing increased (`spaceBefore` 8 → 18) and choice spacing increased (`spaceBefore`/`spaceAfter` 1 → 4) for improved readability
- `ShortAnswer` renders blank space (~4 in) with no underlines

## [0.5.5] — 2026-04-30

### Added
- `promptukit-claude-commands-install` console script — direct alias for `promptukit-claude-commands install` (fixes #7; the hyphenated form is a natural guess and the README's "list/show/install" comment made it look like a separate script)
- `dev/checks/test_create_exam_md.py` — test coverage for the create_exam_md fixes

### Changed
- README clarifies that `promptukit-claude-commands` is a multi-subcommand CLI and lists the new `-install` alias

### Fixed
- `create_exam_md` now matches expected exam-paper formatting (fixes #8):
  - Drops the default `Multiple Choice Examination` subtitle unless metadata explicitly sets a different `exam_type`
  - Choices render with scannable answer markers — open circle (`○`) for choose-one, empty box (`☐`) for choose-multiple — replacing bullet lists
  - `FillInTheBlank` now substitutes the `[blank]` token with a visible answer line in student-facing output
  - `ShortAnswer` blanks render a longer underscore line for handwriting room
  - File-not-found / invalid-JSON cases raise clear errors and the CLI prints them to stderr instead of tracing back

## [0.5.4] — 2026-04-30

### Added
- `promptukit.exams.create_exam_md` — export a question bank to an editable Markdown file; supports all question types (multiple-choice, true/false, short-answer, fill-in-the-blank, matching, calculation) and three answer modes (`none` / `inline` / `key`); `--to-pdf` flag shells out to pandoc for a full JSON → Markdown → PDF pipeline
- `create-exam-md` CLI entry point (mirrors `create_exam.py` CLI shape; adds `--answers` and `--to-pdf` flags)

### Changed
- README development docs now clarify `poetry install` / `poetry run` usage, document `create-pptx`, remove stale `reportlab` install guidance, and tighten CLI PATH notes.

## [0.5.3] — 2026-04-27

### Fixed
- `FillInTheBlank.BLANK_TOKEN` changed from `___` (three underscores) to `[blank]` — avoids conflict with other underscore uses in code and data; `add_question.py` and `validate_question.py` now use the constant; 8 JSON bank entries, all docs, and tests updated
- Stale `block-doku-questions.json` filename references updated across `README.md`, `docs/DATASETS.md`, and three source files to match the actual filename
- Missing `__init__.py` imports that caused `pytest` failures

### Added
- `dev/promptukit_matlab_interop.patch` — MATLAB interoperability patch

## [0.5.2] — 2026-04-24

### Changed
- `paper/outline.md` expanded with handoff notes, inline TODOs, and new sections (Emerging AI-assisted workflows, Functionality, Example workflow, Availability, AI use)
- `paper/ai-use-log.md` logs AI-assisted outline edit round and observations on model opinionation

### Added
- `paper/_old.md` archives prior outline draft for reference

## [0.5.1] — 2026-04-23

### Added
- JOSS-style paper draft scaffold under `paper/` (outline, abstract, figures directory, AI-use log)
- `dev/requirements/matlab_interoperability_plan.md` — scopes MATLAB interop as an optional `examples/matlab/` demo rather than a dependency or full binding layer

## [0.5.0] — 2026-04-23

### Added
- `promptukit.exams.create_pub_quiz` generates a pub-quiz style group trivia PDF with one sheet per round, each carrying team-name / date / score fields for independent grading; supports free-answer, multiple-choice, and true/false questions
- `promptukit/data/question_banks/pub-quiz-sample.json` — 3-round sample bank (Motorsport / Music / Science)

## [0.4.0] — 2026-04-23

### Added
- Non-MCQ question types (`TrueFalse`, `ShortAnswer`, `FillInTheBlank`, `Matching`, `Calculation`) supported in `add_question.py` batch mode and `validate_question.py`; `mixed-types-sample.json` fixture shipped
- `promptukit.claude_commands` package bundles `add-trivia.md` and `audit-trivia.md` as canonical slash-command sources, installable via the new `promptukit-claude-commands` entry point (`list` / `show` / `install`)
- `scripts/sync_claude_commands.py` mirrors canonical command files into `.claude/commands/` and supports `--check` for CI

### Changed
- Release flow rewritten around `scripts/release.py` (bumps `pyproject.toml`, promotes `[Unreleased]`, updates compare links, commits, tags, pushes); `scripts/release.sh` is now a thin Git-Bash wrapper; `RELEASING.md` rewritten around the new flow
- `pyproject.toml` now includes `promptukit/claude_commands/*.md` in both sdist and wheel

## [0.3.0] — 2026-04-23

### Added
- OO question model hierarchy (`question_models.py`) — base `Question` class extensible to new types
- JSON utilities (`json_tools.py`) — load, validate, and migrate question bank files
- Automated tests for question types (`dev/checks/test_question_tool.py`)
- Demo script for question model usage (`scripts/demo_question_usage.py`)
- `parasolpy` dependency integration with skeleton example

### Changed
- `question_bank.py` refactored to delegate to new question model classes
- Upgraded `nicegui` to 3.10.0, `parasolpy` to 0.1.1

## [0.2.2] — 2026-04-21

### Changed
- Updated question bank paths, removed deprecated example file
- Added validation helpers and additional scripts

## [0.2.100] — 2026-04-20

### Added
- Dirty-state indicator and `beforeunload` guard in authoring GUI

## [0.2.000] — 2026-04-20

### Added
- NiceGUI-based authoring GUI (`promptukit.gui`)
- `help()` cheat-sheet via `__init__` and `__main__` entry point
- `--numbers` and `-I` interactive multi-select flags to `question bank extract`

### Fixed
- `RuntimeWarning` from eager subpackage imports in top-level `__init__.py`

[Unreleased]: https://github.com/jrkasprzyk/promptukit/compare/v0.5.5...HEAD
[0.5.5]: https://github.com/jrkasprzyk/promptukit/compare/v0.5.4...v0.5.5
[0.5.4]: https://github.com/jrkasprzyk/promptukit/compare/v0.5.3...v0.5.4
[0.5.3]: https://github.com/jrkasprzyk/promptukit/compare/v0.5.2...v0.5.3
[0.5.2]: https://github.com/jrkasprzyk/promptukit/compare/v0.5.1...v0.5.2
[0.5.1]: https://github.com/jrkasprzyk/promptukit/compare/v0.5.0...v0.5.1
[0.5.0]: https://github.com/jrkasprzyk/promptukit/compare/v0.4.0...v0.5.0
[0.4.0]: https://github.com/jrkasprzyk/promptukit/compare/v0.3.0...v0.4.0
[0.3.0]: https://github.com/jrkasprzyk/promptukit/compare/v0.2.2...v0.3.0
[0.2.2]: https://github.com/jrkasprzyk/promptukit/compare/v0.2.100...v0.2.2
[0.2.100]: https://github.com/jrkasprzyk/promptukit/compare/v0.2.000...v0.2.100
[0.2.000]: https://github.com/jrkasprzyk/promptukit/releases/tag/v0.2.000
