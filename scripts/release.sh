#!/usr/bin/env bash
# Bump the version in pyproject.toml, commit, push, and create + push a
# matching git tag. You still need to publish a GitHub Release manually
# to trigger the PyPI upload workflow.
#
# Usage:  ./scripts/release.sh 0.1.2

set -euo pipefail

if [[ $# -ne 1 ]]; then
    echo "Usage: $0 <new-version>   (e.g. $0 0.1.2)" >&2
    exit 1
fi

NEW_VERSION="$1"
TAG="v${NEW_VERSION}"

if ! [[ "$NEW_VERSION" =~ ^[0-9]+\.[0-9]+\.[0-9]+([a-z0-9.+-]*)?$ ]]; then
    echo "error: '$NEW_VERSION' doesn't look like a semver string (e.g. 0.1.2)" >&2
    exit 1
fi

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$REPO_ROOT"

if [[ -n "$(git status --porcelain)" ]]; then
    echo "error: working tree is dirty. commit or stash changes first." >&2
    git status --short >&2
    exit 1
fi

BRANCH="$(git rev-parse --abbrev-ref HEAD)"
if [[ "$BRANCH" != "main" ]]; then
    echo "warning: you are on branch '$BRANCH', not 'main'." >&2
    read -r -p "continue anyway? [y/N] " reply
    [[ "$reply" =~ ^[Yy]$ ]] || exit 1
fi

if git rev-parse "$TAG" >/dev/null 2>&1; then
    echo "error: tag '$TAG' already exists." >&2
    exit 1
fi

CURRENT="$(grep -E '^version\s*=' pyproject.toml | head -n1 | sed -E 's/.*"([^"]+)".*/\1/')"
echo "bumping $CURRENT -> $NEW_VERSION"

# In-place edit of the first `version = "..."` line under [tool.poetry].
python - "$NEW_VERSION" <<'PY'
import re, sys
path = "pyproject.toml"
new = sys.argv[1]
text = open(path, encoding="utf-8").read()
updated, n = re.subn(
    r'(?m)^(version\s*=\s*")[^"]+(")',
    rf'\g<1>{new}\g<2>',
    text,
    count=1,
)
if n != 1:
    sys.exit(f"error: could not find a version line to update in {path}")
open(path, "w", encoding="utf-8").write(updated)
PY

git add pyproject.toml
git commit -m "bump version to ${NEW_VERSION}"
git push

git tag "$TAG"
git push origin "$TAG"

cat <<EOF

Done. Tag ${TAG} is pushed.

Next step — publish the GitHub Release to trigger the PyPI upload:
  https://github.com/jrkasprzyk/promptukit/releases/new?tag=${TAG}
EOF
