"""Run backend web and worker processes with graceful signal handling.

This replaces Honcho for local and container runtime to ensure clean shutdowns.
"""

from __future__ import annotations

import os
import signal
import subprocess
import sys
import threading
import time
from pathlib import Path
from typing import TextIO

ROOT_DIR = Path(__file__).resolve().parent
IS_WINDOWS = os.name == "nt"
SHUTDOWN_TIMEOUT_SECONDS = 20


def _stream_output(prefix: str, stream: TextIO) -> None:
    for line in iter(stream.readline, ""):
        text = line.rstrip("\n")
        if text:
            print(f"[{prefix}] {text}")


def _start_process(name: str, cmd: list[str]) -> subprocess.Popen[str]:
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
        args=(name, process.stdout),
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
    shutting_down = False

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

    processes["web"] = _start_process("web", web_cmd)
    processes["worker"] = _start_process("worker", worker_cmd)

    try:
        while not shutting_down:
            for name, proc in processes.items():
                exit_code = proc.poll()
                if exit_code is not None:
                    print(f"[{name}] exited with code {exit_code}; stopping all.")
                    shutdown(signal.SIGTERM, None)
                    return exit_code
            time.sleep(0.5)
    finally:
        for name, proc in processes.items():
            _terminate_process(proc, name)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
