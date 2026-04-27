# Changelog

All notable changes to `promptukit` are documented here. The format follows
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/), and this project
adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html) (with
the understanding that during the `0.x` series, minor bumps may contain
breaking changes).

## [Unreleased]

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

[Unreleased]: https://github.com/jrkasprzyk/promptukit/compare/v0.5.2...HEAD
[0.5.2]: https://github.com/jrkasprzyk/promptukit/compare/v0.5.1...v0.5.2
[0.5.1]: https://github.com/jrkasprzyk/promptukit/compare/v0.5.0...v0.5.1
[0.5.0]: https://github.com/jrkasprzyk/promptukit/compare/v0.4.0...v0.5.0
[0.4.0]: https://github.com/jrkasprzyk/promptukit/compare/v0.3.0...v0.4.0
[0.3.0]: https://github.com/jrkasprzyk/promptukit/compare/v0.2.2...v0.3.0
[0.2.2]: https://github.com/jrkasprzyk/promptukit/compare/v0.2.100...v0.2.2
[0.2.100]: https://github.com/jrkasprzyk/promptukit/compare/v0.2.000...v0.2.100
[0.2.000]: https://github.com/jrkasprzyk/promptukit/releases/tag/v0.2.000
