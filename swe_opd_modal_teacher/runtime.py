from __future__ import annotations

import subprocess
import time


def check_running(process: subprocess.Popen) -> None:
    if (returncode := process.poll()) is not None:
        raise subprocess.CalledProcessError(returncode, cmd=process.args)


def wait_ready(process: subprocess.Popen, base_url: str, timeout_seconds: int) -> None:
    import requests

    deadline = time.time() + timeout_seconds
    health_url = f"{base_url}/health"
    while time.time() < deadline:
        try:
            check_running(process)
            response = requests.get(health_url, timeout=5)
            response.raise_for_status()
            return
        except (
            subprocess.CalledProcessError,
            requests.exceptions.ConnectionError,
            requests.exceptions.HTTPError,
            requests.exceptions.Timeout,
        ):
            time.sleep(5)
    raise TimeoutError(f"SGLang server not ready within {timeout_seconds} seconds")


def warmup(
    base_url: str,
    served_model_name: str,
    api_key: str,
    *,
    repeats: int,
    max_tokens: int,
) -> None:
    import requests

    headers = {"Content-Type": "application/json"}
    if api_key:
        headers["Authorization"] = f"Bearer {api_key}"
    payload = {
        "model": served_model_name,
        "messages": [{"role": "user", "content": "Reply with exactly: teacher-warmup-ok"}],
        "temperature": 0.0,
        "max_tokens": max_tokens,
    }
    for _ in range(repeats):
        response = requests.post(
            f"{base_url}/v1/chat/completions",
            headers=headers,
            json=payload,
            timeout=30,
        )
        response.raise_for_status()
