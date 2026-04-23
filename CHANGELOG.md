# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.3.0] - 2026-04-23

### Added
- OO question model hierarchy (`question_models.py`) — base `Question` class extensible to new types
- JSON utilities (`json_tools.py`) — load, validate, and migrate question bank files
- Automated tests for question types (`dev/checks/test_question_tool.py`)
- Demo script for question model usage (`scripts/demo_question_usage.py`)
- `parasolpy` dependency integration with skeleton example

### Changed
- `question_bank.py` refactored to delegate to new question model classes
- Upgraded `nicegui` to 3.10.0, `parasolpy` to 0.1.1

## [0.2.2] - 2026-04-21

### Changed
- Updated question bank paths, removed deprecated example file
- Added validation helpers and additional scripts

## [0.2.100] - 2026-04-20

### Added
- Dirty-state indicator and `beforeunload` guard in authoring GUI

## [0.2.000] - 2026-04-20

### Added
- NiceGUI-based authoring GUI (`promptukit.gui`)
- `help()` cheat-sheet via `__init__` and `__main__` entry point
- `--numbers` and `-I` interactive multi-select flags to `question bank extract`

### Fixed
- `RuntimeWarning` from eager subpackage imports in top-level `__init__.py`
