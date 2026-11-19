#!/bin/bash
# Main build entry point: fetch upstream docs (unless SKIP_DL=1), convert to
# RST, and run sphinx-build.
#
# Usage: html.sh [BUILD_DIR]

set -euo pipefail

cd "$(dirname "$0")"

REPO_DIR="$(pwd)"
SRC_DIR="$REPO_DIR/source"

if [ -z "$1" ]
then
  DEST_DIR="$REPO_DIR/build"
else
  DEST_DIR="$1"
fi
# Prefer a local virtualenv if present.
if [ -f "$REPO_DIR/.venv/bin/activate" ]; then
  # shellcheck disable=SC1091
  source "$REPO_DIR/.venv/bin/activate"
fi

if [ "${SKIP_DL:-0}" != "1" ]; then
  bash scripts/fetch-upstream.sh
fi

log() {
  echo ''
  echo "### ${1} ###"
  echo ''
}

log 'CONVERTING'
python3 scripts/convert.py --docs vendor/haproxy-docs --out source

log 'BUILDING DOCS'
export PYTHONWARNINGS='ignore'
python3 -m sphinx -b html "$SRC_DIR" "$DEST_DIR"

log 'FINISHED'
echo "Site written to $DEST_DIR/"
