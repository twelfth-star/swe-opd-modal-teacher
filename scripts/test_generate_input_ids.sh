#!/usr/bin/env bash

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "${SCRIPT_DIR}/common.sh"

load_env
require_env TEACHER_BASE_URL

AUTH_HEADER=()
if [[ -n "${SGLANG_API_KEY:-}" ]]; then
    AUTH_HEADER=(-H "Authorization: Bearer ${SGLANG_API_KEY}")
fi

payload='{
  "input_ids": [14990],
  "sampling_params": {
    "temperature": 0,
    "max_new_tokens": 0,
    "skip_special_tokens": false
  },
  "return_logprob": true,
  "logprob_start_len": 0
}'

curl -fsS "${TEACHER_BASE_URL%/}/generate" \
  -H 'Content-Type: application/json' \
  "${AUTH_HEADER[@]}" \
  -d "${payload}"
echo
