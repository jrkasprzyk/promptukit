# Releasing

This document describes how to cut a new release of `promptukit`. Publishing is automated by
[`.github/workflows/python-publish.yml`](.github/workflows/python-publish.yml), which fires when
you **publish a GitHub Release** and uploads to PyPI via Trusted Publishing (no API tokens required).

The canonical rule: **the version in `pyproject.toml` and the git tag must match** (`0.3.0` ↔ `v0.3.0`). Everything else follows from that.

## Prerequisites

- Poetry installed (`pipx install poetry` or see the [official docs](https://python-poetry.org/docs/#installation)).
- Python 3 on `PATH` (the release scripts are Python).
- A clean working tree on `main` with all changes to be released already merged.
- Write access to the GitHub repo (to push tags and create releases).

## Quick release (using the script)

The release script bumps `pyproject.toml`, moves `[Unreleased]` content in `CHANGELOG.md` to a new dated section, updates link references, commits both files, and pushes the tag. You still need to publish the GitHub Release manually — that's the deliberate "go" button that triggers the PyPI upload.

1. **Sync and run the tests.**

   ```bash
   git checkout main
   git pull
   poetry install
   poetry run pytest -q
   ```

2. **Make sure `CHANGELOG.md` has entries under `## [Unreleased]`.** These will become the new version's release notes. If the section is empty the script will warn and let you opt in to an empty release.

3. **Run the release script** with the new version.

   Git Bash / macOS / Linux:

   ```bash
   ./scripts/release.sh 0.4.0
   ```

   PowerShell / Windows:

   ```powershell
   python scripts/release.py 0.4.0
   ```

4. **Publish a GitHub Release** to trigger the PyPI upload.

   - **Web UI:** Repo → Releases → "Draft a new release" → select the tag → add release notes → Publish release.
   - **GitHub CLI:**

     ```bash
     gh release create "v$(poetry version -s)" --generate-notes
     ```

   Confirm the release is live:

   ```bash
   gh release list
   ```

5. **Verify** the package is on PyPI: <https://pypi.org/project/promptukit/>

## Manual release (step by step)

Useful when you want to understand what the script does, or when you need to deviate from the standard path.

1. **Sync and verify the working tree is clean.**

   ```bash
   git checkout main
   git pull
   git status
   ```

2. **Install dependencies and run the tests.**

   ```bash
   poetry install
   poetry run pytest -q
   ```

3. **Bump the version.** Use Poetry's `version` command with a semver part or an explicit version.

   Semver guidance:
   - `patch` (`0.1.1` → `0.1.2`): bug fixes, docs
   - `minor` (`0.1.1` → `0.2.0`): new features, backward-compatible
   - `major` (`0.1.1` → `1.0.0`): breaking changes

   ```bash
   poetry version patch   # or minor, major, or an explicit version like 0.4.0
   poetry version         # confirm
   ```

4. **Update `CHANGELOG.md`.** Move everything under `[Unreleased]` to a new `[X.Y.Z] — YYYY-MM-DD` section. Leave an empty `[Unreleased]` heading at the top and update the link references at the bottom:

   ```markdown
   ## [Unreleased]

   ## [0.4.0] — 2026-05-01
   ...

   [Unreleased]: https://github.com/jrkasprzyk/promptukit/compare/v0.4.0...HEAD
   [0.4.0]: https://github.com/jrkasprzyk/promptukit/compare/v0.3.0...v0.4.0
   ```

5. **Commit the version bump and changelog together.**

   ```bash
   git add pyproject.toml CHANGELOG.md
   git commit -m "Release $(poetry version -s)"
   ```

6. **(Optional) Local build sanity check.**

   ```bash
   poetry build
   poetry run twine check dist/*
   ```

7. **Tag and push.** Plain `git push` does not push tags, so both commands are needed:

   ```bash
   git tag "v$(poetry version -s)"
   git push
   git push --tags
   ```

   Verify the tag reached the remote:

   ```bash
   git ls-remote --tags origin
   ```

8. **Publish a GitHub Release** (step 4 of the quick path above).

## Troubleshooting

**PyPI not updated after publishing the GitHub Release** — one of:
- The CI workflow failed. Check the Actions tab on GitHub for errors.
- The version in `pyproject.toml` doesn't match the git tag (e.g. `0.4.0` vs `v0.4.0` — they must match exactly with the `v` prefix only on the tag).

**Tag visible under "Tags" but not "Releases"** — a tag alone does not create a GitHub Release. Publish one from the tag (quick path step 4).

**Script complains about `[Unreleased]` link ref** — `CHANGELOG.md` must contain a `[Unreleased]: <url>/compare/vPREV...HEAD` reference at the bottom. Add one before running the script.

## Rolling back a failed release

PyPI does not allow re-uploading the same version. If a release is broken:

1. Yank the bad version on PyPI (via the web UI).
2. Bump to the next patch version and repeat the release steps.

## One-time setup

For reference, these were configured once and don't need to be redone:

- PyPI Trusted Publisher registered for this repo and workflow
- GitHub repo environment named `pypi` (Settings → Environments)
- `license = "MIT"` declared in `pyproject.toml` with [LICENSE](LICENSE) at the repo root
