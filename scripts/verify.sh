#!/usr/bin/env bash
#
# Smoke-test the deployed modal teacher service.
# Runs three checks: model info, text-based generate, OPD-style input_ids generate.
#
# Usage:
#   bash scripts/verify.sh              # run all checks
#   bash scripts/verify.sh --step N     # run only step N (1-4)
#
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "${SCRIPT_DIR}/common.sh"

load_env

# ── Helpers ──────────────────────────────────────────────────────────

GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[0;33m'
BOLD='\033[1m'
NC='\033[0m'

pass()  { printf "  ${GREEN}PASS${NC}  %s\n" "$*"; }
fail()  { printf "  ${RED}FAIL${NC}  %s\n" "$*"; }
skip()  { printf "  ${YELLOW}SKIP${NC}  %s\n" "$*"; }
step_header() { printf "\n${BOLD}Step %s: %s${NC}\n" "$1" "$2"; }

STEP_ONLY=""
while [[ $# -gt 0 ]]; do
    case "$1" in
        --step) STEP_ONLY="$2"; shift 2 ;;
        *) shift ;;
    esac
done

should_run() {
    [[ -z "${STEP_ONLY}" || "${STEP_ONLY}" == "$1" ]]
}

FAILURES=0

AUTH_HEADER=()
if [[ -n "${SGLANG_API_KEY:-}" ]]; then
    AUTH_HEADER=(-H "Authorization: Bearer ${SGLANG_API_KEY}")
fi

# ── Step 1: Config ───────────────────────────────────────────────────

if should_run 1; then
    step_header 1 "Configuration"

    if [[ -f "${SWE_OPD_MODAL_TEACHER_ROOT}/config/bootstrap/modal_teacher.local.env" ]]; then
        pass "modal_teacher.local.env exists"
    else
        fail "modal_teacher.local.env missing"
        FAILURES=$((FAILURES + 1))
    fi

    if [[ -n "${TEACHER_BASE_URL:-}" ]]; then
        pass "TEACHER_BASE_URL is set: ${TEACHER_BASE_URL}"
    else
        fail "TEACHER_BASE_URL is empty — run: bash scripts/get_url.sh --save"
        FAILURES=$((FAILURES + 1))
    fi
fi

# ── Step 2: /get_model_info ──────────────────────────────────────────

if should_run 2; then
    step_header 2 "/get_model_info"

    if [[ -z "${TEACHER_BASE_URL:-}" ]]; then
        skip "TEACHER_BASE_URL not set"
    else
        if curl -fsS --max-time 30 "${AUTH_HEADER[@]}" "${TEACHER_BASE_URL%/}/get_model_info" >/dev/null 2>&1; then
            pass "GET /get_model_info"
        else
            fail "GET /get_model_info — is the service deployed and running?"
            FAILURES=$((FAILURES + 1))
        fi
    fi
fi

# ── Step 3: /generate (text) ────────────────────────────────────────

if should_run 3; then
    step_header 3 "/generate (text-based)"

    if [[ -z "${TEACHER_BASE_URL:-}" ]]; then
        skip "TEACHER_BASE_URL not set"
    else
        payload='{
          "text": "teacher health check",
          "sampling_params": {"temperature": 0, "max_new_tokens": 0, "skip_special_tokens": false},
          "return_logprob": true,
          "logprob_start_len": 0
        }'
        if curl -fsS --max-time 60 \
            -H 'Content-Type: application/json' \
            "${AUTH_HEADER[@]}" \
            "${TEACHER_BASE_URL%/}/generate" \
            -d "${payload}" >/dev/null 2>&1; then
            pass "POST /generate (text)"
        else
            fail "POST /generate (text)"
            FAILURES=$((FAILURES + 1))
        fi
    fi
fi

# ── Step 4: /generate (input_ids — OPD style) ───────────────────────

if should_run 4; then
    step_header 4 "/generate (input_ids — OPD style)"

    if [[ -z "${TEACHER_BASE_URL:-}" ]]; then
        skip "TEACHER_BASE_URL not set"
    else
        payload='{
          "input_ids": [14990],
          "sampling_params": {"temperature": 0, "max_new_tokens": 0, "skip_special_tokens": false},
          "return_logprob": true,
          "logprob_start_len": 0
        }'
        resp=$(curl -fsS --max-time 60 \
            -H 'Content-Type: application/json' \
            "${AUTH_HEADER[@]}" \
            "${TEACHER_BASE_URL%/}/generate" \
            -d "${payload}" 2>&1) || true

        if echo "${resp}" | python3 -c "import json,sys; d=json.load(sys.stdin); assert 'meta_info' in d and 'input_token_logprobs' in d['meta_info']" 2>/dev/null; then
            pass "POST /generate (input_ids) — meta_info.input_token_logprobs present"
        else
            fail "POST /generate (input_ids) — missing meta_info.input_token_logprobs"
            FAILURES=$((FAILURES + 1))
        fi
    fi
fi

# ── Summary ──────────────────────────────────────────────────────────

printf "\n${BOLD}── Summary ──${NC}\n\n"
if [[ "${FAILURES}" -eq 0 ]]; then
    printf "${GREEN}All checks passed.${NC}\n"
else
    printf "${RED}%d check(s) failed.${NC}\n" "${FAILURES}"
fi
exit "${FAILURES}"
