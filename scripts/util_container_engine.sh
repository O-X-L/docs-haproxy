#!/bin/bash

# CONTAINER_ENGINE_FORCE=docker|podman overrides the auto-detection (podman preferred): needed when an
# image built here must be visible to a specific engine, e.g. docker compose in the e2e suite.
if [ "${CONTAINER_ENGINE_FORCE:-}" = "docker" ]
then
    CONTAINER_ENGINE='docker'
    CONTAINER_ENGINE_ARGS=''

elif [ "${CONTAINER_ENGINE_FORCE:-}" = "podman" ] || which podman >/dev/null
then
    CONTAINER_ENGINE='podman'
    CONTAINER_ENGINE_ARGS='--userns=keep-id'

elif which docker >/dev/null
then
    CONTAINER_ENGINE='docker'
    CONTAINER_ENGINE_ARGS=''

else
    echo "ERROR: No container engine found (podman/docker)"
    exit 1
fi
