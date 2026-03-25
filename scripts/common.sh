#!/usr/bin/env bash

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"

load_env() {
    local env_file="${PROJECT_ROOT}/config/bootstrap/modal_teacher.env"
    local local_env_file="${PROJECT_ROOT}/config/bootstrap/modal_teacher.local.env"
    local selected_file

    if [[ -f "${local_env_file}" ]]; then
        selected_file="${local_env_file}"
    elif [[ -f "${env_file}" ]]; then
        selected_file="${env_file}"
    else
        echo "Missing env file. Create config/bootstrap/modal_teacher.local.env from the example file." >&2
        exit 1
    fi

    set -a
    # shellcheck disable=SC1090
    source "${selected_file}"
    set +a

    export SWE_OPD_MODAL_TEACHER_ROOT="${PROJECT_ROOT}"
    echo "Loaded env from ${selected_file}" >&2
}

require_env() {
    local var_name="$1"
    if [[ -z "${!var_name:-}" ]]; then
        echo "Required env var ${var_name} is not set." >&2
        exit 1
    fi
}
