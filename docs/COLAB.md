Colab Demo
==========

This repository includes a Colab notebook that demonstrates the Quick
Notebook Walkthrough from the README. Use the notebook to run examples in a
hosted environment without local setup.

Open the demo:

https://colab.research.google.com/drive/1vzaUML_8nkWKhOfauv5MXPE-dQ5sXFF_?usp=sharing

How to use
----------

1. Open the link. If prompted, choose `File -> Save a copy in Drive` to edit.
2. Install the package in the notebook (either from PyPI or from the GitHub
   repository):

```python
!pip install promptukit reportlab
# or for the repository HEAD:
!git clone https://github.com/jrkasprzyk/promptukit.git
%cd promptukit
!pip install -e .
```

3. Run the cells. The notebook demonstrates loading the packaged sample
   datasets via `pk.load_resource(...)` when `content/...` isn't available.

Notes
-----
- Installing from the repository installs the version in this repo. Installing
  from PyPI installs the published package. Use whichever fits your needs.
- If you want the notebook copied into this repo, tell me and I will add a
  small `notebooks/` folder containing the .ipynb file.
