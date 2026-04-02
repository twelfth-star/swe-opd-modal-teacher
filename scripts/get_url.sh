#!/usr/bin/env bash
#
# Print the deployed teacher service's public URL.
# Optionally writes it into modal_teacher.local.env if --save is passed.
#
# Usage:
#   bash scripts/get_url.sh          # print URL
#   bash scripts/get_url.sh --save   # print URL and write to local.env
#
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "${SCRIPT_DIR}/common.sh"

load_env
require_env MODAL_APP_NAME

URL=$(python3 -c "
import modal, os
cls = modal.Cls.from_name(os.environ['MODAL_APP_NAME'], 'TeacherServer')
print(cls().serve.get_web_url())
")

if [[ -z "${URL}" ]]; then
    echo "Could not resolve URL. Is the app deployed?" >&2
    exit 1
fi

echo "${URL}"

if [[ "${1:-}" == "--save" ]]; then
    ENV_FILE="${PROJECT_ROOT}/config/bootstrap/modal_teacher.local.env"
    if [[ ! -f "${ENV_FILE}" ]]; then
        echo "No local.env found at ${ENV_FILE}" >&2
        exit 1
    fi
    if grep -q '^TEACHER_BASE_URL=' "${ENV_FILE}"; then
        sed -i "s|^TEACHER_BASE_URL=.*|TEACHER_BASE_URL=${URL}|" "${ENV_FILE}"
    else
        echo "TEACHER_BASE_URL=${URL}" >> "${ENV_FILE}"
    fi
    echo "Saved TEACHER_BASE_URL to ${ENV_FILE}" >&2
fi
