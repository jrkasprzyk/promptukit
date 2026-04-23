# Changelog

All notable changes to `promptukit` are documented here. The format follows
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/), and this project
adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html) (with
the understanding that during the `0.x` series, minor bumps may contain
breaking changes).

## [Unreleased]

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

[Unreleased]: https://github.com/jrkasprzyk/promptukit/compare/v0.3.0...HEAD
[0.3.0]: https://github.com/jrkasprzyk/promptukit/compare/v0.2.2...v0.3.0
[0.2.2]: https://github.com/jrkasprzyk/promptukit/compare/v0.2.100...v0.2.2
[0.2.100]: https://github.com/jrkasprzyk/promptukit/compare/v0.2.000...v0.2.100
[0.2.000]: https://github.com/jrkasprzyk/promptukit/releases/tag/v0.2.000
