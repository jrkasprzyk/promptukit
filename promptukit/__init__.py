"""promptukit — utilities for building question banks and exam documents.

Quick reference (also: python -m promptukit):

  import promptukit
  promptukit.help()          # print this cheat-sheet

Subpackages
-----------
  promptukit.questions       - manage question bank JSON files
  promptukit.exams           - generate exam PDFs (requires reportlab)
  promptukit.gui             - NiceGUI-based authoring GUI (requires nicegui)

CLI tools (run with python -m <module>)
---------------------------------------
  python -m promptukit.questions.question_bank create \\
      --dest path/to/new.json --categories cat1,cat2

  python -m promptukit.questions.question_bank copy \\
      --src old.json --dest new.json

  python -m promptukit.questions.question_bank extract \\
      --src bank.json --dest subset.json \\
      --categories music --difficulty easy

  python -m promptukit.questions.question_bank extract -i \\
      --src bank.json --dest subset.json   # interactive picker

  python -m promptukit.exams.create_exam \\
      -q questions.json -o exam.pdf [-m metadata.json]

  promptukit-gui                         # launch authoring GUI (browser tab)
  promptukit-gui -f my.json              # open an existing file (or start a new one)
  promptukit-gui -p 9000 --no-browser    # custom port, no auto-open

Python API
----------
  from promptukit import load, save, pick, confirm, load_resource, launch_gui

  launch_gui()                              # open the authoring GUI
  launch_gui(file_path="qs.json")           # load/save this file
  launch_gui(port=9000, show=False)         # custom port, no auto-open

  load(path)                 # load any JSON file -> dict/list
  save(path, data)           # save dict/list to JSON
    load_resource('question_banks/crb-water-management-sample.json')  # load bundled data file
  pick("Choose:", options)   # numbered CLI menu -> chosen string
  confirm("Continue?")       # y/n prompt -> bool

  from promptukit.questions.question_bank import filter_questions
  filter_questions(questions, categories=["music"], difficulty="easy")

  from promptukit.exams.create_exam import build_exam_pdf, load_questions_from_json
  build_exam_pdf(questions, "exam.pdf", metadata={...})
"""

from promptukit.utils.cli_helpers import load, save, pick, confirm, load_resource


def launch_gui(*args, **kwargs):
    """Lazy wrapper for ``promptukit.gui.launch`` (avoids importing NiceGUI until used)."""
    from promptukit.gui import launch

    return launch(*args, **kwargs)


__all__ = [
    # subpackages
    "questions",
    "exams",
    "utils",
    # flat re-exports from utils
    "load",
    "save",
    "pick",
    "confirm",
    "load_resource",
    "launch_gui",
    "help",
]

from importlib.metadata import version, PackageNotFoundError
try:
    __version__ = version("promptukit")
except PackageNotFoundError:
    __version__ = "unknown"


def help() -> None:
    """Print a quick-reference cheat-sheet for promptukit."""
    print(__doc__)
