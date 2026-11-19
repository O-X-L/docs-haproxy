#!/bin/bash
# Fetch the upstream HAProxy manuals into vendor/haproxy-docs/ and record the
# source commit SHA for reproducibility.
#
# Usage: fetch-upstream.sh [TARGET_DIR]

set -euo pipefail

cd "$(dirname "$0")/.."

TARGET="${1:-vendor/haproxy-docs}"
UPSTREAM_REPO="https://github.com/haproxy/haproxy"
TMP_DIR="$(mktemp -d)"

cleanup() {
  rm -rf "$TMP_DIR"
}
trap cleanup EXIT

echo "### FETCHING UPSTREAM DOCS ###"
git clone --depth=1 "$UPSTREAM_REPO" "$TMP_DIR/haproxy"

mkdir -p "$TARGET"
cp "$TMP_DIR/haproxy/doc/"*.txt "$TARGET/"
git -C "$TMP_DIR/haproxy" rev-parse HEAD > "$TARGET/COMMIT"

echo "Upstream commit: $(cat "$TARGET/COMMIT")"
echo "Copied $(ls "$TARGET"/*.txt | wc -l) manuals into $TARGET/"
