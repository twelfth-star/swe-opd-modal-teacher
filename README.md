# swe-opd-modal-teacher

Standalone Modal deployment for a fixed-size remote SGLang teacher service.

This repo is intentionally separate from the A/B rollout bootstrap in `swe-opd`.
Its job is only:

- keep exactly `n` Modal replicas alive
- give each replica exactly `m` GPUs
- run one SGLang server per replica with `TP=m`
- expose a stable remote teacher endpoint for OPD-style logprob queries

The intended deployment model is:

- total GPUs: `m * n`
- tensor parallel per replica: `m`
- data-parallel replicas: `n` Modal containers
- no autoscaling beyond the fixed `n` replicas

## Layout

- `modal_app.py`: Modal app entrypoint
- `swe_opd_modal_teacher/settings.py`: environment-backed configuration
- `swe_opd_modal_teacher/runtime.py`: runtime helpers
- `config/bootstrap/modal_teacher.example.env`: example local config
- `scripts/status.sh`: print the current local config summary
- `scripts/prefetch_model.sh`: prefetch model weights into the shared Modal volume
- `scripts/deploy.sh`: deploy the fixed-size teacher service
- `scripts/test_health.sh`: authenticated readiness smoke test
- `scripts/test_generate.sh`: send a minimal text-based `/generate` request
- `scripts/test_generate_input_ids.sh`: send an OPD-style `input_ids` request

## What This Service Actually Runs

This repo implements the following topology:

1. Modal keeps exactly `n` replicas alive by setting `min_containers=max_containers=n`.
2. Each replica requests exactly `m` GPUs via `MODAL_GPU_CONFIG`.
3. Each replica launches one SGLang process with `--tp m`.
4. All replicas serve the same model and tokenizer.
5. The exposed endpoint is used as a remote teacher service for OPD.

For the intended topology:

- `SGLANG_TP_SIZE` should equal the GPU count in `MODAL_GPU_CONFIG`
- `MODAL_DP_REPLICAS`, `MODAL_MIN_CONTAINERS`, and `MODAL_MAX_CONTAINERS` should all be the same value

Example:

- `m = 2`
- `n = 3`

Then:

- total GPUs = `6`
- each Modal replica gets `2` GPUs
- each replica runs `sglang.launch_server --tp 2`
- Modal keeps exactly `3` replicas alive

## Prerequisites

You need:

- a Modal account and working local CLI login
- a Python environment with `modal` available locally
- access to the target Hugging Face model
- a Modal secret for Hugging Face if the model is private

Local setup:

```bash
cd /u/zhe3/re-swe/swe-opd-modal-teacher
pip install -e .
pip install modal
modal setup
```

If the teacher model is private on Hugging Face, create a Modal secret first and then reference it with `MODAL_HF_SECRET_NAME`.

## Configuration

Create your local env file:

```bash
cd /u/zhe3/re-swe/swe-opd-modal-teacher
cp config/bootstrap/modal_teacher.example.env config/bootstrap/modal_teacher.local.env
```

You can inspect the currently loaded values with:

```bash
bash scripts/status.sh
```

The most important config fields are:

- `MODAL_APP_NAME`: Modal app name
- `MODAL_REGION`: region where the teacher containers run
- `MODAL_PROXY_REGIONS`: proxy region for the public endpoint
- `MODAL_GPU_CONFIG`: GPUs per replica, for example `A100:2`
- `MODAL_DP_REPLICAS`: fixed replica count
- `MODAL_MIN_CONTAINERS`: should equal `MODAL_DP_REPLICAS`
- `MODAL_MAX_CONTAINERS`: should equal `MODAL_DP_REPLICAS`
- `SGLANG_MODEL_PATH`: teacher model path or HF repo id
- `SGLANG_MODEL_REVISION`: optional pinned model revision
- `SGLANG_SERVED_MODEL_NAME`: served model name reported by SGLang
- `SGLANG_TP_SIZE`: tensor parallel size inside each replica
- `SGLANG_CONTEXT_LENGTH`: must be large enough for your OPD token sequences
- `SGLANG_API_KEY`: bearer token required by `/generate`
- `SGLANG_EXTRA_ARGS`: additional SGLang args, for example `--trust-remote-code`
- `TEACHER_BASE_URL`: deployed public teacher URL, filled in after deploy

### Recommended Shape For Fixed DP x TP

If you want:

- `n` fixed DP replicas
- `m` GPUs per replica
- `TP = m`

then configure:

```env
MODAL_DP_REPLICAS=n
MODAL_MIN_CONTAINERS=n
MODAL_MAX_CONTAINERS=n
MODAL_GPU_CONFIG=A100:m
SGLANG_TP_SIZE=m
```

### Example Config

This is a representative configuration:

```env
MODAL_APP_NAME=swe-opd-modal-teacher-fixed
MODAL_REGION=us-east
MODAL_PROXY_REGIONS=us-east

N=2
MODAL_DP_REPLICAS=${N}
MODAL_MIN_CONTAINERS=${N}
MODAL_MAX_CONTAINERS=${N}

M=2
MODAL_GPU_CONFIG=A100:${M}
SGLANG_TP_SIZE=${M}

SGLANG_MODEL_PATH=Qwen/Qwen3-8B
SGLANG_MODEL_REVISION=
SGLANG_SERVED_MODEL_NAME=Qwen/Qwen3-8B
SGLANG_CONTEXT_LENGTH=32000
SGLANG_API_KEY=replace-me-with-a-real-token
SGLANG_EXTRA_ARGS=--trust-remote-code

TEACHER_BASE_URL=
```

## End-To-End Workflow

The normal flow is:

1. prepare config
2. prefetch model weights into the shared Modal volume
3. deploy the teacher service
4. resolve the deployed public URL
5. write `TEACHER_BASE_URL`
6. run smoke tests

### Step 1: Check Your Config

```bash
cd /u/zhe3/re-swe/swe-opd-modal-teacher
bash scripts/status.sh
```

Make sure the values printed here are exactly the ones you expect before deploying.

### Step 2: Prefetch The Model

Prefetch downloads model weights into the shared Modal volume without booting the full teacher pool.

```bash
cd /u/zhe3/re-swe/swe-opd-modal-teacher
bash scripts/prefetch_model.sh
```

Expected success signal:

```text
Prefetched <model> into /root/.cache/huggingface
```

Notes:

- this step intentionally forces `MODAL_MIN_CONTAINERS=0` and `MODAL_MAX_CONTAINERS=0`
- it only fills the shared cache volume
- it does not start your fixed `n` teacher replicas

### Step 3: Deploy

Deploy the fixed-size service:

```bash
cd /u/zhe3/re-swe/swe-opd-modal-teacher
bash scripts/deploy.sh
```

This runs:

```bash
modal deploy modal_app.py
```

### Step 4: Resolve The Public URL

After deploy, fetch the stable public URL with Modal:

```bash
cd /u/zhe3/re-swe/swe-opd-modal-teacher
source config/bootstrap/modal_teacher.local.env
python - <<'PY'
import modal
import os

cls = modal.Cls.from_name(os.environ["MODAL_APP_NAME"], "TeacherServer")
print(cls().serve.get_web_url())
PY
```

This should return a URL like:

```text
https://...modal.run
```

Write that into `config/bootstrap/modal_teacher.local.env`:

```env
TEACHER_BASE_URL=https://your-teacher-endpoint.modal.run
```

### Step 5: Smoke Test The Deployment

Run the smoke tests:

```bash
cd /u/zhe3/re-swe/swe-opd-modal-teacher
bash scripts/test_health.sh
bash scripts/test_generate.sh
bash scripts/test_generate_input_ids.sh
```

What each script verifies:

- `test_health.sh`
  checks authenticated `/get_model_info` and then performs one minimal `/generate` smoke request
- `test_generate.sh`
  sends a text-based `/generate` request
- `test_generate_input_ids.sh`
  sends an OPD-style `input_ids` request and is the closest local smoke test to what `slime` OPD uses

### Manual Test Examples

Text-based `/generate`:

```bash
curl -fsS "${TEACHER_BASE_URL%/}/generate" \
  -H 'Content-Type: application/json' \
  -H "Authorization: Bearer ${SGLANG_API_KEY}" \
  -d '{
    "text": "Hello from swe-opd-modal-teacher",
    "sampling_params": {
      "temperature": 0,
      "max_new_tokens": 0,
      "skip_special_tokens": false
    },
    "return_logprob": true,
    "logprob_start_len": 0
  }'
```

OPD-style `input_ids`:

```bash
curl -fsS "${TEACHER_BASE_URL%/}/generate" \
  -H 'Content-Type: application/json' \
  -H "Authorization: Bearer ${SGLANG_API_KEY}" \
  -d '{
    "input_ids": [14990],
    "sampling_params": {
      "temperature": 0,
      "max_new_tokens": 0,
      "skip_special_tokens": false
    },
    "return_logprob": true,
    "logprob_start_len": 0
  }'
```

## Important Operational Notes

### Do Not Use `/health` Or `/health_generate` As Your Success Criterion

In this setup, SGLang's `/health` and `/health_generate` are not reliable readiness probes.
They may return `503` even when authenticated `/generate` and `/get_model_info` are working.

Use these as your real success criteria instead:

- authenticated `GET /get_model_info`
- authenticated `POST /generate`

That is why `scripts/test_health.sh` uses those endpoints rather than `/health`.

### API Key Expectations

This service is expected to run behind bearer auth.

The test scripts automatically send:

```text
Authorization: Bearer ${SGLANG_API_KEY}
```

If you change the key in `modal_teacher.local.env`, redeploy the service before testing again.

### Tokenizer Compatibility

For `slime` OPD, the teacher request is sent with `input_ids`, not raw text.
That means the teacher must use a tokenizer that is compatible with the student rollout tokenizer.

This repo does not enforce tokenizer matching for you.
It assumes you have already chosen a teacher model whose tokenizer matches the student token ids.

## How To Connect This Teacher To `slime` OPD

This repo only provides the remote teacher service.
The actual OPD training loop still lives in `slime`.

### What `slime` Expects

`slime` OPD in `sglang` mode expects:

- a remote teacher endpoint at `--rm-url`
- the teacher endpoint to accept `input_ids`
- the teacher endpoint to return `meta_info.input_token_logprobs`

That matches this service.

Local code references:

- [`on_policy_distillation.py`](/u/zhe3/re-swe/slime/slime/rollout/on_policy_distillation.py)
- [`arguments.py`](/u/zhe3/re-swe/slime/slime/utils/arguments.py)
- [`run-qwen3-8B-opd.sh`](/u/zhe3/re-swe/slime/examples/on_policy_distillation/run-qwen3-8B-opd.sh)

### `slime` Args To Use

You need the standard OPD args:

```bash
--use-opd
--opd-type sglang
--opd-kl-coef 1.0
--custom-rm-path slime.rollout.on_policy_distillation.reward_func
--custom-reward-post-process-path slime.rollout.on_policy_distillation.post_process_rewards
```

And then point `slime` at this deployed teacher:

```bash
--rm-url "${TEACHER_BASE_URL%/}/generate"
--rm-api-key "${SGLANG_API_KEY}"
```

`slime` in this workspace has been patched to support:

- `--rm-api-key`

That token is sent as:

```text
Authorization: Bearer <token>
```

### Minimal Integration Snippet

If you are modifying a `slime` launch script, the reward-model / teacher section should look like this:

```bash
RM_ARGS=(
  --custom-rm-path slime.rollout.on_policy_distillation.reward_func
  --custom-reward-post-process-path slime.rollout.on_policy_distillation.post_process_rewards
  --rm-url "${TEACHER_BASE_URL%/}/generate"
  --rm-api-key "${SGLANG_API_KEY}"
)

GRPO_ARGS=(
  --advantage-estimator grpo
  --use-opd
  --opd-type sglang
  --opd-kl-coef 1.0
  --use-kl-loss
  --kl-loss-coef 0.00
  --kl-loss-type low_var_kl
  --entropy-coef 0.00
)
```

### Minimal End-To-End `slime` Example

Assuming:

- the teacher service is already deployed
- `TEACHER_BASE_URL` is the deployed Modal URL
- `SGLANG_API_KEY` is the bearer token expected by the teacher

then the teacher-specific OPD args are:

```bash
--custom-rm-path slime.rollout.on_policy_distillation.reward_func \
--custom-reward-post-process-path slime.rollout.on_policy_distillation.post_process_rewards \
--rm-url "${TEACHER_BASE_URL%/}/generate" \
--rm-api-key "${SGLANG_API_KEY}" \
--use-opd \
--opd-type sglang \
--opd-kl-coef 1.0
```

### Important `slime` Notes

- do not use `--opd-teacher-load` when `--opd-type sglang`
- the remote teacher URL should point to `/generate`
- the teacher must support `input_ids`
- the teacher must return token logprobs
- the teacher and student tokenizers must be compatible

## Troubleshooting

### `test_health.sh` Fails With `401`

This means the local `SGLANG_API_KEY` and the deployed service key do not match.

Fix:

1. check `config/bootstrap/modal_teacher.local.env`
2. confirm `SGLANG_API_KEY`
3. redeploy with `bash scripts/deploy.sh`
4. rerun the smoke tests

### `test_health.sh` Or `test_generate.sh` Fails With `503`

Possible causes:

- the service has not finished starting yet
- the wrong URL is in `TEACHER_BASE_URL`
- you are checking `/health` instead of `/get_model_info` or `/generate`

Use:

```bash
bash scripts/test_health.sh
```

instead of curling `/health` directly.

### You Changed Env But Modal Still Uses Old Values

This usually means you edited `modal_teacher.local.env` but have not redeployed yet.

Fix:

```bash
bash scripts/deploy.sh
```

The deployed service only reflects the new config after redeploy.

### Prefetch Starts The Whole Teacher Pool

That should not happen anymore.
`scripts/prefetch_model.sh` explicitly forces:

- `MODAL_MIN_CONTAINERS=0`
- `MODAL_MAX_CONTAINERS=0`

so prefetch only fills the shared cache volume.

## Summary

If you only want the shortest working sequence:

```bash
cd /u/zhe3/re-swe/swe-opd-modal-teacher
cp config/bootstrap/modal_teacher.example.env config/bootstrap/modal_teacher.local.env
vim config/bootstrap/modal_teacher.local.env
bash scripts/status.sh
bash scripts/prefetch_model.sh
bash scripts/deploy.sh
source config/bootstrap/modal_teacher.local.env
python - <<'PY'
import modal
import os
cls = modal.Cls.from_name(os.environ["MODAL_APP_NAME"], "TeacherServer")
print(cls().serve.get_web_url())
PY
# write the output into TEACHER_BASE_URL
bash scripts/test_health.sh
bash scripts/test_generate.sh
bash scripts/test_generate_input_ids.sh
```

Then point `slime` OPD at:

```bash
--rm-url "${TEACHER_BASE_URL%/}/generate"
--rm-api-key "${SGLANG_API_KEY}"
```
