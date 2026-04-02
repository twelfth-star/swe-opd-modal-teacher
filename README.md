# swe-opd-modal-teacher

Deploy a fixed-size remote SGLang teacher service on [Modal](https://modal.com) for on-policy distillation (OPD). This repo is part of the [swe-opt-training](https://github.com/twelfth-star/swe-opt-training) pipeline.

The service:
- keeps exactly `N` Modal replicas alive (`min_containers = max_containers = N`)
- gives each replica exactly `M` GPUs
- runs one SGLang server per replica with `--tp M`
- exposes a stable public endpoint that accepts `input_ids` and returns token-level log-probabilities

Related repos:
- [swe-opt-training](https://github.com/twelfth-star/swe-opt-training) — OPD training loop (calls this teacher)
- [swe-opd-remote-docker](https://github.com/twelfth-star/swe-opd-remote-docker) — distributed rollout infrastructure

## Quick Start

### 1. Install prerequisites

```bash
pip install -e .
pip install modal
modal setup   # authenticate with your Modal account
```

Each team member needs their own Modal account. Sign up at https://modal.com if you don't have one.

### 2. Run the setup wizard

```bash
bash scripts/setup.sh
```

This creates `config/bootstrap/modal_teacher.local.env` (gitignored) with your settings. The wizard prompts for model path, GPU topology, API key, etc.

To check if config already exists:

```bash
bash scripts/setup.sh --check
```

### 3. Prefetch model weights

Downloads model into Modal's shared cache volume without starting any GPU replicas:

```bash
bash scripts/prefetch_model.sh
```

### 4. Deploy

```bash
bash scripts/deploy.sh
```

### 5. Get the public URL

```bash
bash scripts/get_url.sh --save
```

This resolves the deployed URL and writes it to `TEACHER_BASE_URL` in your local config.

### 6. Verify

```bash
bash scripts/verify.sh
```

Tests config, `/get_model_info`, text-based `/generate`, and OPD-style `input_ids` `/generate`.

---

## Setup Guide for New Teammates

### What you need

1. **A Modal account** — sign up at https://modal.com (free tier available)
2. **Python 3.11+** with `modal` and `requests` installed
3. **Access to the teacher model on HuggingFace** (if it's a gated/private model, you'll need a HF token)

### Step-by-step

1. **Clone this repo**:
   ```bash
   git clone git@github.com:twelfth-star/swe-opd-modal-teacher.git
   cd swe-opd-modal-teacher
   ```

2. **Install**:
   ```bash
   pip install -e .
   pip install modal
   ```

3. **Authenticate with Modal**:
   ```bash
   modal setup
   ```
   This opens a browser for OAuth login. Each person uses their own Modal account.

4. **If the model is private on HuggingFace**, create a Modal secret:
   ```bash
   modal secret create huggingface-secret HF_TOKEN=hf_your_token_here
   ```
   Then set `MODAL_HF_SECRET_NAME=huggingface-secret` in your config.

5. **Run the setup wizard**:
   ```bash
   bash scripts/setup.sh
   ```

6. **Deploy and test**:
   ```bash
   bash scripts/prefetch_model.sh
   bash scripts/deploy.sh
   bash scripts/get_url.sh --save
   bash scripts/verify.sh
   ```

### What is personal vs shared

| Item | Shared | Personal |
|------|--------|----------|
| This repo's code and scripts | shared (git) | — |
| `modal_teacher.example.env` | shared (git) | — |
| `modal_teacher.local.env` | — | personal (gitignored) |
| Modal account & auth | — | personal |
| Modal app deployment | — | personal (each person deploys their own) |
| HF model weights | shared (same HF repo) | — |

---

## Configuration Reference

All config lives in `config/bootstrap/modal_teacher.local.env`. The system loads `.local.env` first, falls back to `.env`, and errors if neither exists.

### Preset configs

Several preset configurations are provided as starting points:

| File | Model | GPUs |
|------|-------|------|
| `modal_teacher.example.env` | Qwen/Qwen3-8B | 2x A100 (tp=2) |
| `modal_teacher_qwen35_35b.env` | Qwen/Qwen3.5-35B-A3B-FP8 | 4x A100-40GB (tp=4) |
| `modal_teacher_qwen3_coder_next.env` | Qwen/Qwen3-30B-A3B-Instruct-2507 | 2x A100-80GB (tp=2) |

Copy any preset to `modal_teacher.local.env` and edit as needed.

### Variables

| Variable | Default | Description |
|----------|---------|-------------|
| **Modal infrastructure** | | |
| `MODAL_APP_NAME` | `swe-opd-modal-teacher` | App identifier (must be unique per Modal account) |
| `MODAL_REGION` | `us-east` | Container region |
| `MODAL_PROXY_REGIONS` | `us-east` | Proxy region(s) for public endpoint |
| `MODAL_GPU_CONFIG` | `A100:2` | GPU spec per replica (e.g. `A100-80GB:4`) |
| `MODAL_DP_REPLICAS` | `2` | Fixed replica count (N) |
| `MODAL_MIN_CONTAINERS` | same as N | Must equal `MODAL_DP_REPLICAS` |
| `MODAL_MAX_CONTAINERS` | same as N | Must equal `MODAL_DP_REPLICAS` |
| `MODAL_TARGET_INPUTS` | `4` | Max concurrent requests per replica |
| `MODAL_SCALEDOWN_WINDOW_SECONDS` | `1800` | Idle time before scaledown (30 min) |
| `MODAL_BASE_IMAGE` | SGLang v0.5.6 image | Docker base image |
| `MODAL_HF_SECRET_NAME` | (empty) | Modal secret for private HF models |
| `MODAL_HF_CACHE_VOLUME_NAME` | `swe-opd-modal-teacher-hf-cache` | Shared cache volume name |
| **SGLang server** | | |
| `SGLANG_MODEL_PATH` | `Qwen/Qwen3-8B` | HuggingFace model ID |
| `SGLANG_MODEL_REVISION` | (empty) | Pinned model revision |
| `SGLANG_SERVED_MODEL_NAME` | same as model path | Name in API responses |
| `SGLANG_TP_SIZE` | `1` | Tensor parallelism (must equal GPU count in `MODAL_GPU_CONFIG`) |
| `SGLANG_MEM_FRACTION_STATIC` | `0.80` | GPU memory fraction for KV cache |
| `SGLANG_CONTEXT_LENGTH` | `0` | Max context (0 = model default) |
| `SGLANG_API_KEY` | `CHANGE_ME` | Bearer token for authentication |
| `SGLANG_EXTRA_ARGS` | (empty) | Extra SGLang flags (e.g. `--trust-remote-code`) |
| **Timeouts & warmup** | | |
| `PREFETCH_TIMEOUT_SECONDS` | `7200` | Model download timeout |
| `SGLANG_STARTUP_TIMEOUT_SECONDS` | `1800` | Server startup timeout |
| `SGLANG_ENABLE_WARMUP` | `true` | Run warmup requests after startup |
| `SGLANG_WARMUP_REPEATS` | `2` | Number of warmup requests |
| **Deployment state** | | |
| `TEACHER_BASE_URL` | (empty) | Public endpoint URL (filled after deploy via `get_url.sh`) |

### GPU topology

If you want `N` replicas with `M` GPUs each (TP = M):

```env
MODAL_DP_REPLICAS=N
MODAL_MIN_CONTAINERS=N
MODAL_MAX_CONTAINERS=N
MODAL_GPU_CONFIG=A100:M
SGLANG_TP_SIZE=M
```

Total GPUs = N x M.

---

## API

The deployed service exposes SGLang's native endpoints. The training code in [swe-opt-training](https://github.com/twelfth-star/swe-opt-training) calls `POST /generate` with `input_ids`.

### POST /generate (OPD usage)

This is the primary endpoint used by the training pipeline.

**Request:**
```json
{
  "input_ids": [14990, 1234, 5678],
  "sampling_params": {
    "temperature": 0,
    "max_new_tokens": 0,
    "skip_special_tokens": false
  },
  "return_logprob": true,
  "logprob_start_len": 0
}
```

**Headers:**
```
Content-Type: application/json
Authorization: Bearer <SGLANG_API_KEY>
```

**Response** (relevant fields):
```json
{
  "meta_info": {
    "input_token_logprobs": [
      [logprob_value, token_id],
      [logprob_value, token_id],
      ...
    ]
  }
}
```

The training code extracts `meta_info.input_token_logprobs` and uses the per-token log-probabilities as the distillation signal.

### GET /get_model_info

Returns model metadata. Used as a health check (more reliable than `/health`).

### Important: do not use /health as readiness check

SGLang's `/health` endpoint is unreliable in this setup — it may return 503 even when `/generate` and `/get_model_info` work fine. Always use `/get_model_info` or `/generate` instead.

---

## Directory Structure

```
scripts/
  setup.sh                  # Interactive config wizard
  verify.sh                 # Smoke test deployed service
  get_url.sh                # Resolve and save public URL
  status.sh                 # Print current config summary
  prefetch_model.sh         # Download model weights (no GPU)
  deploy.sh                 # Deploy to Modal
  common.sh                 # Shared shell helpers
  test_health.sh            # Test /get_model_info + /generate
  test_generate.sh          # Test text-based /generate
  test_generate_input_ids.sh  # Test OPD-style input_ids /generate

config/bootstrap/
  modal_teacher.example.env           # Template config
  modal_teacher_qwen35_35b.env        # Preset: Qwen3.5-35B on 4x A100
  modal_teacher_qwen3_coder_next.env  # Preset: Qwen3-30B on 2x A100-80GB

modal_app.py                          # Modal app entrypoint
swe_opd_modal_teacher/
  settings.py                         # Environment-backed configuration
  runtime.py                          # Runtime helpers (health check, warmup)
```

## Integration with swe-opt-training

The training code calls the teacher via two environment variables:

```env
SWE_TEACHER_URL=https://your-app.modal.run/generate
SWE_TEACHER_API_KEY=your-api-key
```

These are set in the training pipeline's config. The teacher URL should point to `/generate` (not the base URL).

For slime OPD integration, the relevant args are:

```bash
--rm-url "${TEACHER_BASE_URL%/}/generate"
--rm-api-key "${SGLANG_API_KEY}"
--use-opd
--opd-type sglang
--opd-kl-coef 1.0
```

## Troubleshooting

**401 Unauthorized** — API key mismatch. Check `SGLANG_API_KEY` in your local.env matches what was deployed. Redeploy after fixing.

**503 Service Unavailable** — Service may still be starting, or you're hitting `/health` instead of `/get_model_info`. Wait a few minutes and retry with `bash scripts/verify.sh`.

**Config changes not reflected** — You must redeploy after editing local.env: `bash scripts/deploy.sh`.

**Prefetch downloads too slowly** — Make sure `hf_transfer` is working (it's installed automatically in the container image).

**GPU cost** — Modal charges per second of GPU usage. Stop your deployment when not in use by scaling to zero or deleting the app: `modal app stop <app-name>`.
