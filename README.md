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
promptukit-gui          # launch the browser-based authoring GUI
```

You can also import the library in Python or a Jupyter notebook:

```python
import promptukit as pk
# Top-level helpers: pk.load(path), pk.save(path, data), pk.pick(), pk.confirm()
# Launch the authoring GUI: pk.launch_gui()
# Subpackages are available as `pk.exams`, `pk.questions`, and `pk.utils`.
```

Quick Notebook Walkthrough
-------------------------

Here are short, copy-pasteable examples you can run inside a Jupyter notebook to
load a question bank, validate it, and generate a PDF exam.

```python
# 1) Import helpers
import promptukit as pk
from promptukit.questions import validate_question
from promptukit.exams import create_exam

# 2) Load a question bank (path relative to the repository root). If you're
# running outside the repository (for example from an installed package),
# fall back to the packaged sample dataset that ships with `promptukit`.
import os
bank_path = 'content/question_banks/example_sections.json'
if os.path.exists(bank_path):
   data = pk.load(bank_path)
else:
   # load packaged sample included with the installed package
   data = pk.load_resource('question_banks/example_sections.json')

# 3) Inspect the file (section-based vs flat list)
if 'sections' in data:
   print('Sections:', [s.get('title') for s in data['sections']])
   print('First question:', data['sections'][0]['questions'][0])
elif 'questions' in data:
   print('Total questions:', len(data['questions']))
   print('First question:', data['questions'][0])
else:
   print('Unexpected file shape:', type(data))

# 4) Validate programmatically
errors, warnings = validate_question.validate(data)
if errors:
   print('Validation errors:', errors)
else:
   print('Bank valid — warnings:', warnings)

# 5) Generate a PDF exam from the same bank (we already have `data` loaded
# above as a dict, so pass it directly). Note: PDF generation requires
# the `reportlab` package: `pip install reportlab`.
create_exam.build_exam_pdf(data, 'notebooks/output_exam.pdf')

```

Notes
-----
- If you only want to run the library functions without Poetry activation, you
  can run modules with `python -m promptukit.questions.extract_question` or
  `python -m promptukit.exams.create_exam` as shown elsewhere in this README.
- Generating PDFs requires `reportlab` (install with `pip install reportlab`).

Try the interactive Colab demo
------------------------------

If you'd like a runnable notebook that demonstrates the Quick Notebook
Walkthrough, open the Colab demo:

https://colab.research.google.com/drive/1vzaUML_8nkWKhOfauv5MXPE-dQ5sXFF_?usp=sharing

Quick tips for Colab:

- To use the published package on PyPI:

```python
!pip install promptukit reportlab
```

- To run the repository version (latest changes), clone and install from GitHub:

```python
!git clone https://github.com/jrkasprzyk/promptukit.git
%cd promptukit
!pip install -e .
```

- The Colab notebook includes cells that use `pk.load_resource(...)` as a
   fallback when local `content/` files aren't available.

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

Authoring GUI (NiceGUI)
-----------------------

`promptukit` ships a lightweight browser GUI for authoring multiple-choice
question banks without touching Python. It reads and writes the same JSON
format used by the rest of the package (the one validated by
`validate-question`), so you can open any existing bank in
`promptukit/data/question_banks/` (or your own) and edit it in place.

Launch from the shell:

```bash
promptukit-gui                                  # opens http://localhost:8080 in a browser tab
promptukit-gui -f my_bank.json                  # load (or create) this working file
promptukit-gui -p 9000 --no-browser             # custom port, don't auto-open a tab
```

`-f/--file` points at the GUI's *working file* — if it exists it's loaded on
startup; when you click **Save all to file** it gets overwritten with the
current in-memory list. You can also change the working file from inside the
GUI via the top-bar **Open…** button.

Or from Python:

```python
from promptukit import launch_gui
launch_gui()                                     # defaults: ./promptukit_questions.json, port 8080
launch_gui(file_path="my_bank.json", port=9000, show=False)
```

The GUI is a single page with a resizable splitter: question list on the left,
editor on the right. Each list row shows the full prompt (wrapping as needed)
plus `id`, `category`, and a color-coded `difficulty` badge. The editor exposes
every field in the schema:

- `id` (text)
- `category` (text with autocomplete from the file's `categories` list)
- `difficulty` (easy / medium / hard)
- `prompt` (autosizing textarea)
- `choices` (four inputs A–D, with a radio to pick which one is `answer`)
- `quip_correct`, `quip_wrong` (optional textareas — omitted from the saved
  file when blank, matching the existing banks' convention)

Top-bar buttons:

- **Open…** — switch the working file (loads it if it exists, or starts empty
  with that path queued for the next save).
- **Reload from file** — discard in-memory edits and re-read the working file.
- **Save all to file** — the only action that writes to the current working
  file, so you can discard a session.
- **Save as…** — write the in-memory bank to a new path and switch the working
  file to it (existing files are not overwritten unless you opt in).
- **Copy all as JSON** — full bank (including `categories` / `_schema_notes`).
- **Copy selected as JSON** — the single-question dict, ready to paste into
  another bank's `questions` array.

The editor's **Apply** button commits edits to the in-memory list (the
top-bar Save writes them to disk).

On-disk format (unchanged from the rest of the package):

```json
{
  "_schema_notes": ["optional free-form notes"],
  "categories": ["music", "motorsport"],
  "questions": [
    {
      "id": "music_001",
      "category": "music",
      "difficulty": "easy",
      "prompt": "Which instrument has a keyboard and strings?",
      "choices": ["Guitar", "Piano", "Violin", "Drums"],
      "answer": 1,
      "quip_correct": "Yep.",
      "quip_wrong": "Nope."
    }
  ]
}
```

Unknown top-level keys and unknown per-question keys are preserved verbatim on
round-trip, so the GUI is safe to point at files with extra metadata it
doesn't understand.

Requires `nicegui` (installed automatically as a dependency).

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

