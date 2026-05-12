import os
import sys
from importlib.metadata import version as get_version, PackageNotFoundError

sys.path.insert(0, os.path.abspath('..'))

project = 'promptukit'
copyright = '2026, Joseph Kasprzyk'
author = 'Joseph Kasprzyk'

try:
    release = get_version('promptukit')
except PackageNotFoundError:
    release = 'unknown'

extensions = [
    'sphinx.ext.autodoc',
    'sphinx.ext.napoleon',
    'sphinx.ext.viewcode',
]

exclude_patterns = ['_build']

html_theme = 'furo'

autodoc_member_order = 'bysource'
