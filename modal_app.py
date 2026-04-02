from __future__ import annotations

import subprocess
from pathlib import Path

import modal

from swe_opd_modal_teacher.settings import settings

app = modal.App(settings.modal_app_name)

HF_CACHE_VOL = modal.Volume.from_name(settings.modal_hf_cache_volume_name, create_if_missing=True)

image = (
    modal.Image.from_registry(settings.modal_base_image)
    .entrypoint([])
    # hf_transfer for fast model weight downloads
    .pip_install("hf_transfer")
    .add_local_dir(
        Path(__file__).resolve().parent / "swe_opd_modal_teacher",
        remote_path="/root/swe_opd_modal_teacher",
        copy=True,
    )
    .env(settings.modal_env() | {"HF_HUB_CACHE": settings.hf_cache_path, "HF_HOME": settings.hf_home_path, "HF_HUB_ENABLE_HF_TRANSFER": "1"})
)

if settings.modal_hf_secret_name:
    _secrets = [modal.Secret.from_name(settings.modal_hf_secret_name)]
else:
    _secrets = []


@app.function(
    image=image,
    volumes={settings.hf_cache_path: HF_CACHE_VOL},
    secrets=_secrets,
    timeout=settings.prefetch_timeout_seconds,
)
def prefetch_model() -> None:
    from huggingface_hub import snapshot_download

    snapshot_download(
        repo_id=settings.sglang_model_path,
        revision=settings.sglang_model_revision or None,
        cache_dir=settings.hf_cache_path,
    )
    HF_CACHE_VOL.commit()
    print(f"Prefetched {settings.sglang_model_path} into {settings.hf_cache_path}")


@app.cls(
    image=image,
    gpu=settings.modal_gpu_config,
    region=settings.modal_region,
    min_containers=settings.modal_min_containers,
    max_containers=settings.modal_max_containers,
    scaledown_window=settings.modal_scaledown_window_seconds,
    volumes={settings.hf_cache_path: HF_CACHE_VOL},
    secrets=_secrets,
)
@modal.concurrent(
    target_inputs=settings.modal_target_inputs,
    max_inputs=settings.modal_target_inputs,
)
class TeacherServer:
    @modal.web_server(
        port=settings.sglang_port,
        startup_timeout=settings.startup_timeout_seconds,
    )
    def serve(self) -> None:
        cmd = settings.build_sglang_command()
        print("Launching SGLang:")
        print(" ".join(cmd))
        self.process = subprocess.Popen(cmd, start_new_session=True)

    @modal.exit()
    def shutdown(self) -> None:
        process = getattr(self, "process", None)
        if process is None:
            return
        if process.poll() is None:
            process.terminate()
            try:
                process.wait(timeout=20)
            except subprocess.TimeoutExpired:
                process.kill()


@app.local_entrypoint()
def main() -> None:
    repo_root = Path(__file__).resolve().parent
    print(f"Repo root           : {repo_root}")
    print(f"Modal app name      : {settings.modal_app_name}")
    print(f"Modal region        : {settings.modal_region}")
    print(f"Proxy regions       : {settings.modal_proxy_regions}")
    print(f"GPU config          : {settings.modal_gpu_config}")
    print(f"Fixed DP replicas   : {settings.modal_min_containers}")
    print(f"Max replicas        : {settings.modal_max_containers}")
    print(f"SGLang TP size      : {settings.sglang_tp_size}")
    print(f"SGLang model path   : {settings.sglang_model_path}")
    print(f"Served model name   : {settings.sglang_served_model_name}")
    print(f"Health URL (local)  : {settings.local_base_url}/health")
    print(f"Generate URL (local): {settings.local_base_url}/generate")
