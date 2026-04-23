#!/usr/bin/env bash
# Thin wrapper around scripts/release.py so Git Bash / macOS / Linux users
# can run `./scripts/release.sh 0.1.2`. All logic lives in release.py.
#
# Usage:  ./scripts/release.sh 0.1.2

set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
exec python "$SCRIPT_DIR/release.py" "$@"
