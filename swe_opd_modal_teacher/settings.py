from __future__ import annotations

import os
import shlex
from dataclasses import dataclass


def _get_str(name: str, default: str = "") -> str:
    return os.environ.get(name, default).strip()


def _get_int(name: str, default: int) -> int:
    raw = os.environ.get(name)
    return default if raw is None or raw.strip() == "" else int(raw)


def _get_float(name: str, default: float) -> float:
    raw = os.environ.get(name)
    return default if raw is None or raw.strip() == "" else float(raw)


def _get_bool(name: str, default: bool) -> bool:
    raw = os.environ.get(name)
    if raw is None or raw.strip() == "":
        return default
    value = raw.strip().lower()
    if value in {"1", "true", "yes", "y", "on"}:
        return True
    if value in {"0", "false", "no", "n", "off"}:
        return False
    raise ValueError(f"Unsupported boolean value for {name}: {raw}")


def _get_csv(name: str, default: str) -> list[str]:
    raw = _get_str(name, default)
    return [item.strip() for item in raw.split(",") if item.strip()]


@dataclass(frozen=True)
class Settings:
    modal_app_name: str
    modal_region: str
    modal_proxy_regions: list[str]
    modal_gpu_config: str
    modal_min_containers: int
    modal_max_containers: int
    modal_target_inputs: int
    modal_scaledown_window_seconds: int
    modal_exit_grace_period_seconds: int
    modal_base_image: str
    modal_hf_secret_name: str
    modal_hf_cache_volume_name: str
    hf_cache_path: str
    hf_home_path: str
    prefetch_timeout_seconds: int
    startup_timeout_seconds: int
    enable_warmup: bool
    warmup_repeats: int
    warmup_max_tokens: int
    sglang_model_path: str
    sglang_model_revision: str
    sglang_served_model_name: str
    sglang_host: str
    sglang_port: int
    sglang_tp_size: int
    sglang_mem_fraction_static: float
    sglang_context_length: int
    sglang_api_key: str
    sglang_extra_args: str

    @property
    def local_base_url(self) -> str:
        return f"http://127.0.0.1:{self.sglang_port}"

    def modal_env(self) -> dict[str, str]:
        return {
            "MODAL_APP_NAME": self.modal_app_name,
            "MODAL_REGION": self.modal_region,
            "MODAL_PROXY_REGIONS": ",".join(self.modal_proxy_regions),
            "MODAL_GPU_CONFIG": self.modal_gpu_config,
            "MODAL_MIN_CONTAINERS": str(self.modal_min_containers),
            "MODAL_MAX_CONTAINERS": str(self.modal_max_containers),
            "MODAL_TARGET_INPUTS": str(self.modal_target_inputs),
            "MODAL_SCALEDOWN_WINDOW_SECONDS": str(self.modal_scaledown_window_seconds),
            "MODAL_EXIT_GRACE_PERIOD_SECONDS": str(self.modal_exit_grace_period_seconds),
            "MODAL_BASE_IMAGE": self.modal_base_image,
            "MODAL_HF_CACHE_VOLUME_NAME": self.modal_hf_cache_volume_name,
            "HF_CACHE_PATH": self.hf_cache_path,
            "HF_HOME_PATH": self.hf_home_path,
            "PREFETCH_TIMEOUT_SECONDS": str(self.prefetch_timeout_seconds),
            "SGLANG_STARTUP_TIMEOUT_SECONDS": str(self.startup_timeout_seconds),
            "SGLANG_ENABLE_WARMUP": "true" if self.enable_warmup else "false",
            "SGLANG_WARMUP_REPEATS": str(self.warmup_repeats),
            "SGLANG_WARMUP_MAX_TOKENS": str(self.warmup_max_tokens),
            "SGLANG_MODEL_PATH": self.sglang_model_path,
            "SGLANG_MODEL_REVISION": self.sglang_model_revision,
            "SGLANG_SERVED_MODEL_NAME": self.sglang_served_model_name,
            "SGLANG_HOST": self.sglang_host,
            "SGLANG_PORT": str(self.sglang_port),
            "SGLANG_TP_SIZE": str(self.sglang_tp_size),
            "SGLANG_MEM_FRACTION_STATIC": str(self.sglang_mem_fraction_static),
            "SGLANG_CONTEXT_LENGTH": str(self.sglang_context_length),
            "SGLANG_API_KEY": self.sglang_api_key,
            "SGLANG_EXTRA_ARGS": self.sglang_extra_args,
        }

    def build_sglang_command(self) -> list[str]:
        command = [
            "python",
            "-m",
            "sglang.launch_server",
            "--model-path",
            self.sglang_model_path,
            "--served-model-name",
            self.sglang_served_model_name,
            "--host",
            self.sglang_host,
            "--port",
            str(self.sglang_port),
            "--tp",
            str(self.sglang_tp_size),
            "--mem-fraction-static",
            str(self.sglang_mem_fraction_static),
            "--api-key",
            self.sglang_api_key,
        ]
        if self.sglang_model_revision:
            command.extend(["--revision", self.sglang_model_revision])
        if self.sglang_context_length > 0:
            command.extend(["--context-length", str(self.sglang_context_length)])
        if self.sglang_extra_args:
            command.extend(shlex.split(self.sglang_extra_args))
        return command


settings = Settings(
    modal_app_name=_get_str("MODAL_APP_NAME", "swe-opd-modal-teacher"),
    modal_region=_get_str("MODAL_REGION", "us-east"),
    modal_proxy_regions=_get_csv("MODAL_PROXY_REGIONS", _get_str("MODAL_REGION", "us-east")),
    modal_gpu_config=_get_str("MODAL_GPU_CONFIG", "A100:1"),
    modal_min_containers=_get_int("MODAL_MIN_CONTAINERS", _get_int("MODAL_DP_REPLICAS", 1)),
    modal_max_containers=_get_int("MODAL_MAX_CONTAINERS", _get_int("MODAL_DP_REPLICAS", 1)),
    modal_target_inputs=_get_int("MODAL_TARGET_INPUTS", 4),
    modal_scaledown_window_seconds=_get_int("MODAL_SCALEDOWN_WINDOW_SECONDS", 1800),
    modal_exit_grace_period_seconds=min(_get_int("MODAL_EXIT_GRACE_PERIOD_SECONDS", 25), 25),
    modal_base_image=_get_str("MODAL_BASE_IMAGE", "lmsysorg/sglang:v0.5.6.post2-cu129-amd64-runtime"),
    modal_hf_secret_name=_get_str("MODAL_HF_SECRET_NAME", ""),
    modal_hf_cache_volume_name=_get_str("MODAL_HF_CACHE_VOLUME_NAME", "swe-opd-modal-teacher-hf-cache"),
    hf_cache_path=_get_str("HF_CACHE_PATH", "/root/.cache/huggingface"),
    hf_home_path=_get_str("HF_HOME_PATH", "/root/.cache/huggingface"),
    prefetch_timeout_seconds=_get_int("PREFETCH_TIMEOUT_SECONDS", 7200),
    startup_timeout_seconds=_get_int("SGLANG_STARTUP_TIMEOUT_SECONDS", 1800),
    enable_warmup=_get_bool("SGLANG_ENABLE_WARMUP", True),
    warmup_repeats=_get_int("SGLANG_WARMUP_REPEATS", 2),
    warmup_max_tokens=_get_int("SGLANG_WARMUP_MAX_TOKENS", 8),
    sglang_model_path=_get_str("SGLANG_MODEL_PATH", "Qwen/Qwen3-8B"),
    sglang_model_revision=_get_str("SGLANG_MODEL_REVISION", ""),
    sglang_served_model_name=_get_str("SGLANG_SERVED_MODEL_NAME", _get_str("SGLANG_MODEL_PATH", "Qwen/Qwen3-8B")),
    sglang_host=_get_str("SGLANG_HOST", "0.0.0.0"),
    sglang_port=_get_int("SGLANG_PORT", 8000),
    sglang_tp_size=_get_int("SGLANG_TP_SIZE", 1),
    sglang_mem_fraction_static=_get_float("SGLANG_MEM_FRACTION_STATIC", 0.8),
    sglang_context_length=_get_int("SGLANG_CONTEXT_LENGTH", 0),
    sglang_api_key=_get_str("SGLANG_API_KEY", "EMPTY"),
    sglang_extra_args=_get_str("SGLANG_EXTRA_ARGS", ""),
)
