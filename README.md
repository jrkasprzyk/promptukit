PromptuKit
=========

Small utilities for working with trivia question banks.

Getting started (Poetry)
------------------------

1. Install Poetry (if you don't have it).

   ```bash
   pip install --user poetry
   ```

2. Create the virtual environment and install dependencies:

   ```bash
   poetry install
   ```

3. Run the CLI tools via Poetry:

   ```bash
   poetry run promptukit-add-trivia
   poetry run promptukit-extract-trivia --help
   poetry run promptukit-validate-trivia
   ```

Activating the virtualenv
-------------------------

If Poetry is configured to create an in-project virtualenv, it will be placed in a `.venv` folder at the repository root. Activate that environment from the project root using the command for your shell:

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
poetry shell        # spawn a shell inside the project's virtualenv
poetry run <cmd>    # run a single command inside the virtualenv, e.g. `poetry run pytest`
```

Notes
-----
- The package entry points are defined in `pyproject.toml` and map
  to the `main()` functions in the modules under the `promptukit`
  package.
- If you prefer an interactive shell, use `poetry shell` then invoke
  the commands directly.

Usage Examples
--------------

Here are a few concrete examples showing the included CLI tools. Replace
the paths shown with your own files when needed.

Quick (Poetry):

```bash
poetry run promptukit-add-trivia
poetry run promptukit-extract-trivia --list-categories
poetry run promptukit-validate-trivia
```

Extracting data:

```bash
# List categories and available fields
poetry run promptukit-extract-trivia --list-categories

# Print prompt and answer fields for the 'music' category
poetry run promptukit-extract-trivia --file question_banks/block-doku-questions.json --category music --fields prompt,answer

# Interactive picker
poetry run promptukit-extract-trivia -i
```

Validate a trivia file:

```bash
# Validate the default question bank
poetry run promptukit-validate-trivia

# Validate a specific file
poetry run promptukit-validate-trivia question_banks/block-doku-questions.json
```

Manage files with `trivia_tool` (create/copy/extract):

```bash
# Create a new template JSON file
poetry run promptukit-trivia-tool create --dest question_banks/new.json --categories music,film-and-tv

# Copy an existing file
poetry run promptukit-trivia-tool copy --src question_banks/block-doku-questions.json --dest question_banks/backup.json

# Extract a subset (easy music questions)
poetry run promptukit-trivia-tool extract --src question_banks/block-doku-questions.json --dest question_banks/music_easy.json --categories music --difficulty easy

# Interactive extract
poetry run promptukit-trivia-tool extract -i --src question_banks/block-doku-questions.json --dest question_banks/pick.json
```

Alternative: run modules with `python -m` when not using Poetry:

```bash
python -m promptukit.add_trivia
python -m promptukit.extract_trivia --help
python -m promptukit.trivia_tool create --dest question_banks/new.json
```

Create exam PDF
---------------

The `create_exam.py` script can generate a printable exam PDF. It now accepts an external JSON question bank so you can build exams from your existing `question_banks/` files.

Usage (from the repository root):

```bash
# Use the built-in hard-coded exam
python -m promptukit.create_exam

# Load questions from a JSON bank and write a PDF
python -m promptukit.create_exam -q question_banks/block-doku-questions.json -o cven4333_from_json.pdf

# With Poetry (runs the module inside the virtualenv)
poetry run python -m promptukit.create_exam -q question_banks/block-doku-questions.json -o cven4333_from_json.pdf
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

- If choices are not already labeled (for example `"Oceans"` instead of `"A) Oceans"`), the script will prefix them with `A)`, `B)`, etc. Prompts without a leading number will be auto-numbered sequentially.

Example files
-------------

- Example section-based bank: [question_banks/example_sections.json](question_banks/example_sections.json)
- JSON Schema describing accepted layouts: [question_banks/question_schema.json](question_banks/question_schema.json)

Behavior notes
--------------

- If no `-q/--questions` file is provided, the script falls back to the built-in hard-coded 60-question exam and preserves its original 8-section breakdown.
- When you provide a section-based JSON file the PDF's section headings will be taken from each section's `title` (or `name` / `label` if present). When you provide a flat list with `category` fields, the loader will group questions by category to build sections automatically.


Running Tests
-------------

The test suite lives in the tests directory. The file [tests/test_trivia_tool.py](tests/test_trivia_tool.py)
contains unit tests and a small integration-style test that exercise the CLI functions.

What the test covers:

- `test_filter_questions`: verifies `filter_questions()` handles category, `difficulty`, `ids`, and `match` filters.
- `test_cmd_extract_and_create_and_copy`: writes temporary JSON files and invokes `promptukit.trivia_tool.main()` with
   CLI-style arguments to test `extract`, `create`, and `copy`.

Run the tests:

Using Poetry (recommended):

```bash
poetry add --dev pytest
poetry run pytest tests/test_trivia_tool.py -q
```

Or run directly if pytest is available on your PATH:

```bash
python -m pytest tests/test_trivia_tool.py -q
```

Notes:
- Tests use pytest's `tmp_path` fixture and do not modify your repository files.

