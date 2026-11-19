#!/bin/bash

set -euo pipefail

cd "$(dirname "$0")/.."

source ./scripts/util_container_engine.sh

PATH_REPO="$(pwd)"

read -p "Re-Build the image? [yes|NO] " build_prompt
if echo "$build_prompt" | grep -Eq 'y|Y'
then
  echo ''
  echo '### BUILDING ###'
  echo ''
  "$CONTAINER_ENGINE" build -t localhost/opencode -f "${PATH_REPO}/ai/DockerfileOpenCode" --network=host  --build-arg UID=$(id -u) --no-cache "${PATH_REPO}/ai/"
fi

echo ''
echo '### RUNNING ###'
echo ''
mkdir -p "${PATH_REPO}/.opencode/repos/"
chmod 700 "${PATH_REPO}/.opencode/"

"$CONTAINER_ENGINE" run -it --rm --name "owrt-claude-$(date '+%s')" \
  --network=host \
  --privileged \
  -v "$(pwd):/workspace:rw" \
  -v "${PATH_REPO}/.opencode/:/home/coder/.local/:rw" $CONTAINER_ENGINE_ARGS \
  localhost/opencode:latest
