#!/usr/bin/env bash

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "${SCRIPT_DIR}/common.sh"

load_env

echo "Repo root           : ${SWE_OPD_MODAL_TEACHER_ROOT}"
echo "Modal app name      : ${MODAL_APP_NAME:-}"
echo "Modal region        : ${MODAL_REGION:-}"
echo "Proxy regions       : ${MODAL_PROXY_REGIONS:-}"
echo "GPU config          : ${MODAL_GPU_CONFIG:-}"
echo "DP replicas         : ${MODAL_DP_REPLICAS:-}"
echo "Min containers      : ${MODAL_MIN_CONTAINERS:-}"
echo "Max containers      : ${MODAL_MAX_CONTAINERS:-}"
echo "SGLang model path   : ${SGLANG_MODEL_PATH:-}"
echo "SGLang served name  : ${SGLANG_SERVED_MODEL_NAME:-}"
echo "SGLang TP size      : ${SGLANG_TP_SIZE:-}"
echo "Teacher base URL    : ${TEACHER_BASE_URL:-<unset>}"
