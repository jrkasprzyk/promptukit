DATASETS and Packaged Samples
=============================

This document explains how packaged sample datasets are organised, how to load
them from an installed `promptukit` package, and how to add new packaged
resources when you want to ship additional banks.

Where packaged data lives
------------------------

- Packaged sample datasets live under the package path `promptukit/data/`.
- Question banks are grouped under `promptukit/data/question_banks/`.

Loading packaged samples in code
-------------------------------

Use the convenience function exposed at the package top-level:

```python
import promptukit as pk

# Load a packaged sample by relative path under 'question_banks'
data = pk.load_resource('question_banks/example_sections.json')

# The function returns a Python object loaded from JSON (usually a dict).
```

Notebook-friendly fallback
--------------------------

If your notebook runs inside the repository tree you may prefer to load the
local `content/` files during development. Example pattern used in the
README notebook examples:

```python
import os
import promptukit as pk

local = 'content/question_banks/example_sections.json'
if os.path.exists(local):
    data = pk.load(local)
else:
    data = pk.load_resource('question_banks/example_sections.json')
```

Adding new packaged datasets
----------------------------

1. Place the JSON file under `promptukit/data/question_banks/`.
2. Follow the project's common shapes: either a top-level `questions` array or
   a `sections` array of objects with a `title` and `questions` array.
3. If needed, add a small unit test in `dev/checks/` that exercises loading
   and (optionally) validation using `promptukit.questions.validate_question`.
4. Ensure the file is included in the distribution (see pyproject.toml).

Packaging notes
---------------

- `pyproject.toml` contains an `include` section that ensures files under
  `promptukit/data/**` are included in source distributions. If you add new
  resources, update the patterns if you place them elsewhere.
- To verify packaged files are present in a built wheel or sdist:

```bash
poetry build
tar -tvf dist/<package>-<version>.tar.gz | grep promptukit/data
unzip -l dist/<package>-<version>-py3-none-any.whl | grep promptukit/data
```

Access via importlib.resources
------------------------------

Internally `pk.load_resource` uses `importlib.resources` so files are
accessible whether the package is installed from source, an sdist, or a
wheel. When adding binary or non-JSON resources, prefer to extend
`pk.load_resource` or add a separate helper that knows how to open that format.

Questions or next steps
-----------------------

- Want me to also bundle the full `block-doku-questions.json` and other
  large banks verbatim into the package? I can add them, but note this will
  increase package size and may not be necessary for example usage.
- I can add a quick test that verifies `pk.load_resource(...)` returns JSON
  for each packaged file.
