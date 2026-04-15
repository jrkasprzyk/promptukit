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

Notes
-----
- The package entry points are defined in `pyproject.toml` and map
  to the `main()` functions in the modules under the `promptukit`
  package.
- If you prefer an interactive shell, use `poetry shell` then invoke
  the commands directly.
