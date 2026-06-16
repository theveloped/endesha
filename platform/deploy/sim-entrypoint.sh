#!/usr/bin/env bash
# Sim-container entrypoint: source the FROZEN pixi env activation (captured at
# build time into /activate.sh) then exec the given command through the env
# python. We never call `pixi run` here — it re-syncs the env to the lock and
# would revert the PyOpenGL 3.1.7 override pyrender's OSMesa backend needs.
set -euo pipefail
# shellcheck disable=SC1091
source /activate.sh
exec "$@"
