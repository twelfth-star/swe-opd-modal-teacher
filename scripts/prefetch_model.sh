#!/usr/bin/env bash

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "${SCRIPT_DIR}/common.sh"

load_env

cd "${SWE_OPD_MODAL_TEACHER_ROOT}"

# Prefetch should only populate the shared model cache volume.
# Force the fixed teacher pool to stay disabled during this run so we do not
# accidentally boot the full `n` replicas just to download weights.
export MODAL_MIN_CONTAINERS=0
export MODAL_MAX_CONTAINERS=0

exec modal run modal_app.py::prefetch_model
