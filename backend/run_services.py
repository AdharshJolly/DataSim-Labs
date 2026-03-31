"""Run backend web and worker processes with graceful signal handling."""

from __future__ import annotations

from collections import deque
import json
import os
import signal
import subprocess
import sys
import threading
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Deque
from typing import TextIO

ROOT_DIR = Path(__file__).resolve().parent
IS_WINDOWS = os.name == "nt"
SHUTDOWN_TIMEOUT_SECONDS = 20
MAX_RECENT_LOG_LINES = 200
UPSTASH_LIMIT_ERROR_TEXT = "max requests limit exceeded"


def _parse_env_bool(name: str, default: bool = False) -> bool:
    raw = os.getenv(name)
    if raw is None:
        return default
    return raw.strip().lower() in {"1", "true", "yes", "on"}


def _stream_output(prefix: str, stream: TextIO, recent_lines: Deque[str]) -> None:
    for line in iter(stream.readline, ""):
        text = line.rstrip("\n")
        if text:
            recent_lines.append(text)
            print(f"[{prefix}] {text}")


def _worker_hit_upstash_limit(recent_lines: Deque[str]) -> bool:
    return any(UPSTASH_LIMIT_ERROR_TEXT in line.lower() for line in recent_lines)


def _worker_state_file_path() -> Path:
    configured = os.getenv("WORKER_HEALTH_STATE_FILE", ".worker-health.json").strip()
    filename = Path(configured).name or ".worker-health.json"
    return ROOT_DIR / filename


def _clear_worker_state_file() -> None:
    state_path = _worker_state_file_path()
    if state_path.exists():
        state_path.unlink(missing_ok=True)


def _write_worker_state_degraded(reason: str) -> None:
    state_path = _worker_state_file_path()
    payload = {
        "status": "degraded",
        "reason": reason,
        "updated_at": datetime.now(timezone.utc).isoformat(),
    }
    state_path.write_text(json.dumps(payload), encoding="utf-8")


def _start_process(
    name: str, cmd: list[str], recent_lines: Deque[str]
) -> subprocess.Popen[str]:
    creationflags = subprocess.CREATE_NEW_PROCESS_GROUP if IS_WINDOWS else 0
    process = subprocess.Popen(
        cmd,
        cwd=str(ROOT_DIR),
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        bufsize=1,
        creationflags=creationflags,
    )
    assert process.stdout is not None
    thread = threading.Thread(
        target=_stream_output,
        args=(name, process.stdout, recent_lines),
        daemon=True,
    )
    thread.start()
    return process


def _terminate_process(proc: subprocess.Popen[str], name: str) -> None:
    if proc.poll() is not None:
        return

    try:
        if IS_WINDOWS:
            proc.send_signal(signal.CTRL_BREAK_EVENT)
        else:
            proc.terminate()
    except Exception:
        pass

    try:
        proc.wait(timeout=SHUTDOWN_TIMEOUT_SECONDS)
    except subprocess.TimeoutExpired:
        print(f"[{name}] did not stop in time; killing process.")
        proc.kill()


def main() -> int:
    python_exec = sys.executable
    port = os.getenv("PORT", "8000")

    processes: dict[str, subprocess.Popen[str]] = {}
    recent_output: dict[str, Deque[str]] = {}
    shutting_down = False
    worker_disabled_due_to_upstash_limit = False

    def shutdown(_signum: int, _frame) -> None:  # type: ignore[no-untyped-def]
        nonlocal shutting_down
        if shutting_down:
            return
        shutting_down = True
        print("[manager] shutdown signal received, stopping services...")

        for name, proc in processes.items():
            _terminate_process(proc, name)

    signal.signal(signal.SIGINT, shutdown)
    signal.signal(signal.SIGTERM, shutdown)

    web_cmd = [
        python_exec,
        "-m",
        "uvicorn",
        "app.main:app",
        "--host",
        "0.0.0.0",
        "--port",
        str(port),
    ]
    worker_cmd = [
        python_exec,
        "-m",
        "celery",
        "-A",
        "app.worker.celery_app:celery_app",
        "worker",
        "--pool=solo",
        "--concurrency=1",
        "--loglevel=info",
        "--without-mingle",
        "--without-gossip",
        "--without-heartbeat",
    ]

    async_generation_enabled = _parse_env_bool("ASYNC_GENERATION_ENABLED", False)
    worker_auto_disable = _parse_env_bool("WORKER_AUTO_DISABLE_ON_UPSTASH_LIMIT", True)
    _clear_worker_state_file()

    recent_output["web"] = deque(maxlen=MAX_RECENT_LOG_LINES)
    processes["web"] = _start_process("web", web_cmd, recent_output["web"])
    if async_generation_enabled:
        recent_output["worker"] = deque(maxlen=MAX_RECENT_LOG_LINES)
        processes["worker"] = _start_process(
            "worker", worker_cmd, recent_output["worker"]
        )
    else:
        print("[manager] ASYNC_GENERATION_ENABLED=false; worker process not started.")

    try:
        while not shutting_down:
            for name, proc in list(processes.items()):
                exit_code = proc.poll()
                if exit_code is not None:
                    if (
                        name == "worker"
                        and worker_auto_disable
                        and _worker_hit_upstash_limit(
                            recent_output.get(
                                "worker", deque(maxlen=MAX_RECENT_LOG_LINES)
                            )
                        )
                    ):
                        worker_disabled_due_to_upstash_limit = True
                        processes.pop("worker", None)
                        recent_output.pop("worker", None)
                        _write_worker_state_degraded(
                            "upstash_max_requests_limit_exceeded"
                        )
                        print(
                            "[manager] worker disabled due to Upstash max request limit; web will continue running."
                        )
                        continue

                    print(f"[{name}] exited with code {exit_code}; stopping all.")
                    shutdown(signal.SIGTERM, None)
                    return exit_code

            if worker_disabled_due_to_upstash_limit:
                worker_disabled_due_to_upstash_limit = False
                print(
                    "[manager] To re-enable async jobs, restore Redis quota and restart the container."
                )
            time.sleep(0.5)
    finally:
        for name, proc in processes.items():
            _terminate_process(proc, name)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
