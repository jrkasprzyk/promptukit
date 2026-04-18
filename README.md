PromptuKit
==========

Utilities for building and managing multiple-choice question banks and
generating exam PDFs.

Install from PyPI
-----------------

```bash
pip install promptukit
```

The package is published at https://pypi.org/project/promptukit/. After
installing you get the CLI entry points on your PATH:

```bash
add-question
extract-question --help
validate-question
question-bank --help
```

You can also import the library in Python or a Jupyter notebook:

```python
from promptukit.exams import create_exam
from promptukit.questions import extract_question, validate_question
```

Getting started (Poetry, for development)
-----------------------------------------

1. Install Poetry (if you don't have it):

   ```bash
   pip install --user poetry
   ```

2. Create the virtual environment and install dependencies:

   ```bash
   poetry install
   ```

3. Run the CLI tools via Poetry (console scripts / entry points):

   ```bash
   poetry run add-question
   poetry run extract-question --help
   poetry run validate-question
   poetry run question-bank --help
   ```

Activating the virtualenv
-------------------------

If Poetry is configured to create an in-project virtualenv, it will be
placed in a `.venv` folder at the repository root. Activate that
environment from the project root using the command for your shell.

PowerShell (Windows):

```powershell
.\.venv\Scripts\Activate.ps1
```

If script execution is blocked, temporarily allow it then activate:

```powershell
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
.\.venv\Scripts\Activate.ps1
```

Command Prompt (cmd.exe):

```cmd
.\.venv\Scripts\activate.bat
```

Git Bash / MSYS (Windows):

```bash
source .venv/Scripts/activate
```

macOS / Linux (POSIX):

```bash
source .venv/bin/activate
```

Alternatives (no manual activation required):

```bash
# Run a single command inside the virtualenv without activating it
poetry run <cmd>    # e.g. poetry run pytest
```

Poetry 2.x note:

- The `poetry shell` command (which previously spawned a new shell) is not
  installed by default in Poetry 2.0+. You can either use
  `poetry env activate` (then evaluate the printed activation command in
  your shell) or install the shell plugin to restore `poetry shell`.

Notes
-----
- The package entry points are defined in `pyproject.toml` under
  `[tool.poetry.scripts]` and map console script names to the
  `main()` functions in the modules under the `promptukit` package.

Usage Examples
--------------

Quick (Poetry):

```bash
poetry run add-question
poetry run extract-question --list-categories
poetry run validate-question
poetry run question-bank extract --help
```

Extracting data:

```bash
# List categories and available fields
poetry run extract-question --list-categories

# Print prompt and answer fields for the 'music' category
poetry run extract-question --file content/question_banks/block-doku-questions.json --category music --fields prompt,answer

# Interactive picker
poetry run extract-question -i
```

Add questions:

```bash
# Interactive add
poetry run add-question

# Batch mode
poetry run add-question --batch new_questions.json content/question_banks/mybank.json
```

Validate a trivia file:

```bash
# Validate the default question bank
poetry run validate-question

# Validate a specific file
poetry run validate-question content/question_banks/block-doku-questions.json
```

Manage files with `question-bank` (create/copy/extract):

```bash
# Create a new template JSON file
poetry run question-bank create --dest content/question_banks/new.json --categories music,film-and-tv

# Copy an existing file
poetry run question-bank copy --src content/question_banks/block-doku-questions.json --dest content/question_banks/backup.json

# Extract a subset (easy music questions)
poetry run question-bank extract --src content/question_banks/block-doku-questions.json --dest content/question_banks/music_easy.json --categories music --difficulty easy

# Interactive extract
poetry run question-bank extract -i --src content/question_banks/block-doku-questions.json --dest content/question_banks/pick.json
```

Alternative: run modules with `python -m` when not using Poetry:

```bash
python -m promptukit.questions.add_question
python -m promptukit.questions.extract_question --help
python -m promptukit.questions.question_bank create --dest content/question_banks/new.json
```

Create exam PDF
---------------

The `create_exam.py` script can generate a printable exam PDF. It accepts
an external JSON question bank so you can build exams from your existing
`content/question_banks/` files.

Usage (from the repository root):

```bash
# Use the built-in hard-coded exam
python -m promptukit.exams.create_exam

# Load questions from a JSON bank and write a PDF
python -m promptukit.exams.create_exam -q content/question_banks/block-doku-questions.json -o cven4333_from_json.pdf

# With Poetry (runs the module inside the virtualenv)
poetry run python -m promptukit.exams.create_exam -q content/question_banks/block-doku-questions.json -o cven4333_from_json.pdf
```

Supported JSON formats
----------------------

- Top-level `sections` (preferred):

  ```json
  {
     "sections": [
        {
           "title": "Section title",
           "questions": [ { "prompt": "...", "choices": ["...", "..."] }, ... ]
        }
     ]
  }
  ```

- `categories` is an alias for `sections` and is also accepted.

- Flat list of questions (top-level array) or top-level object with `questions` array:

  ```json
  {
     "questions": [ { "prompt": "...", "choices": ["...", "..."], "category": "Section title" }, ... ]
  }
  ```

- Question objects support multiple common field names: `prompt`, `q`, `question`, or `text` for the question text; `choices` or `answers` for the answer options; optional `category` to group flat lists into sections.

- If choices are not already labeled (for example "Oceans" instead of "A) Oceans"), the script will prefix them with `A)`, `B)`, etc. Prompts without a leading number will be auto-numbered sequentially.

Example files
-------------

- Example section-based bank: [content/question_banks/example_sections.json](content/question_banks/example_sections.json)
- JSON Schema describing accepted layouts: [content/question_banks/question_schema.json](content/question_banks/question_schema.json)

Behavior notes
--------------

- If no `-q/--questions` file is provided to the exam generator, the script
  falls back to the built-in hard-coded 60-question exam and preserves its
  original 8-section breakdown.
- When you provide a section-based JSON file the PDF's section headings will
  be taken from each section's `title` (or `name` / `label` if present). When
  you provide a flat list with `category` fields, the loader will group
  questions by category to build sections automatically.

Running Tests
-------------

The test suite lives under `dev/checks`. The file
`dev/checks/test_question_tool.py` contains unit tests that exercise the
question-bank helpers and CLI-style interfaces.

Run the tests:

Using Poetry (recommended):

```bash
poetry install
poetry run pytest -q
```

Or run a single file directly:

```bash
poetry run pytest dev/checks/test_question_tool.py -q
```

Notes:

- Tests use pytest's `tmp_path` fixture and do not modify your repository files.

