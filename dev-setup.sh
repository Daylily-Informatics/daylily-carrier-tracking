#!/bin/sh
# Dev setup for daylily-carrier-tracking.
#
# Goal: make it hard to accidentally install into system/base Python.
# This script *always* installs using ./.venv/bin/python -m pip.
#
# Usage:
#   ./dev-setup.sh      # create/update .venv + editable install (does NOT activate your shell)
#   . ./dev-setup.sh    # same, and activates .venv in the current shell session

set -eu

REPO_ROOT=$(CDPATH= cd "$(dirname "$0")" && pwd)
cd "$REPO_ROOT"

VENV_DIR="$REPO_ROOT/.venv"
VENV_PY="$VENV_DIR/bin/python"

_is_sourced() {
  # `return` is only valid when this script is sourced.
  (return 0 2>/dev/null)
}

_find_python() {
  if command -v python3 >/dev/null 2>&1; then
    command -v python3
    return 0
  fi
  if command -v python >/dev/null 2>&1; then
    command -v python
    return 0
  fi
  return 1
}

if [ ! -d "$VENV_DIR" ] || [ ! -x "$VENV_PY" ]; then
  PY_CREATE=$(_find_python) || {
    echo "ERROR: Need python3 (or python) on PATH to create .venv" >&2
    exit 127
  }
  echo "Creating virtualenv: $VENV_DIR" >&2
  "$PY_CREATE" -m venv "$VENV_DIR"
fi

if [ ! -x "$VENV_PY" ]; then
  echo "ERROR: venv python missing: $VENV_PY" >&2
  exit 1
fi

# Ensure pip exists inside the venv.
if ! "$VENV_PY" -m pip --version >/dev/null 2>&1; then
  echo "Bootstrapping pip inside venv (ensurepip)..." >&2
  "$VENV_PY" -m ensurepip --upgrade
fi

echo "Installing (editable) into venv: $VENV_DIR" >&2
"$VENV_PY" -m pip install -e .

echo "Done." >&2

if _is_sourced; then
  # shellcheck disable=SC1091
  . "$VENV_DIR/bin/activate"
  echo "Activated: $VENV_DIR" >&2
else
  echo "To activate for this shell:" >&2
  echo "  . ./.venv/bin/activate" >&2
fi

