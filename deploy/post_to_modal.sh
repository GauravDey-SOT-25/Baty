#!/bin/sh
set -eu

ROOT=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
PYTHON="$ROOT/work/modal-cli-venv/bin/python"

if [ ! -x "$PYTHON" ]; then
  echo "Modal CLI environment is missing. See deploy/README-modal.md for setup." >&2
  exit 2
fi

if ! "$PYTHON" -c 'import modal' >/dev/null 2>&1; then
  echo "Modal SDK is unavailable in work/modal-cli-venv." >&2
  exit 2
fi

if ! "$PYTHON" -m modal token info >/dev/null 2>&1; then
  echo "Modal account sign-in is not available. Run: $PYTHON -m modal setup" >&2
  exit 2
fi

cd "$ROOT"
exec "$PYTHON" -m modal deploy deploy/modal_app.py "$@"
