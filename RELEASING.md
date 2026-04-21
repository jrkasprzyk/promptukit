Releasing promptukit
====================

This is the end-to-end checklist for shipping a new version of `promptukit`
to PyPI. The release is automated by
[.github/workflows/python-publish.yml](.github/workflows/python-publish.yml),
which fires when you **publish a GitHub Release** and uses PyPI Trusted
Publishing (no API tokens).

The canonical rule: **the version in `pyproject.toml` and the git tag
must match** (`0.1.2` ↔ `v0.1.2`). Everything else follows from that.

Release checklist
-----------------

1. **Make your changes** on `main` and run the tests:

   ```bash
   poetry run pytest -q
   ```

2. **Bump the version** in [pyproject.toml](pyproject.toml) (the `version`
   line under `[tool.poetry]`). PyPI rejects re-uploads of an existing
   version, so this step is mandatory for every release.

   Semver guidance:

   - Patch (`0.1.1` → `0.1.2`): bug fixes, docs
   - Minor (`0.1.1` → `0.2.0`): new features, backward-compatible
   - Major (`0.1.1` → `1.0.0`): breaking changes

   Poetry can also be used to do the bump:

 ```bash
# bump semver parts
poetry version patch
poetry version minor
poetry version major

# set an exact version
poetry version 0.3.0
```

3. **Commit and push** the bump:

   ```bash
   git commit -am "bump version to 0.1.2"
   git push
   ```

4. **(Optional) Local build sanity check**:

   ```bash
   poetry build
   poetry run twine check dist/*
   ```

5. **Tag and push** the release tag:

   ```bash
   git tag v0.1.2
   git push origin v0.1.2
   ```

6. **Publish a GitHub Release** — on github.com go to
   *Releases → Draft a new release*, pick the tag `v0.1.2`, write short
   release notes, and click **Publish release**. This fires the workflow
   and ships to PyPI automatically.

7. **Verify** the release landed:

   Check [the package's page on PyPi](https://pypi.org/project/promptukit/).

   
   TODO: In a future update, we'll make sure the releasing instructions refer to the poetry version of the commands, see [the post here](https://www.geeksforgeeks.org/python/updating-dependencies-in-python-poetry/) in the meantime.

   For example, you can update the version of `promptukit` in your repository with:

   ```bash
   poetry update promptukit   
   ```

Shortcut
--------

Steps 2, 3, and 5 are automated by a release script that bumps `pyproject.toml`,
commits, pushes, and creates + pushes the matching `v0.1.2` tag. You still need
to publish the GitHub Release (step 6) manually — that's the deliberate "go" button.

Git Bash / macOS / Linux:

```bash
./scripts/release.sh 0.1.2
```

PowerShell / Windows (works anywhere Python is available):

```powershell
python scripts/release.py 0.1.2
```

One-time setup (already done)
-----------------------------

For reference, these were configured once and don't need to be redone:

- PyPI Trusted Publisher registered for this repo and workflow
- GitHub repo environment named `pypi` (Settings → Environments)
- `license = "MIT"` declared in `pyproject.toml` with [LICENSE](LICENSE)
  at the repo root
