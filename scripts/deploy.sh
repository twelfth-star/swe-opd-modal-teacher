#!/usr/bin/env bash

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "${SCRIPT_DIR}/common.sh"

load_env

cd "${SWE_OPD_MODAL_TEACHER_ROOT}"
exec modal deploy modal_app.py
