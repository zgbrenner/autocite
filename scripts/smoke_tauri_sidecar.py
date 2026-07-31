#!/usr/bin/env python3
"""Start a packaged sidecar and verify its authenticated loopback API."""

from __future__ import annotations

import argparse
import json
import os
import socket
import subprocess
import sys
import tempfile
import time
import urllib.error
import urllib.request
from pathlib import Path


def available_port() -> int:
    with socket.socket() as listener:
        listener.bind(("127.0.0.1", 0))
        return int(listener.getsockname()[1])


def request_json(url: str, token: str | None = None) -> dict[str, object]:
    headers = {"Accept": "application/json"}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    request = urllib.request.Request(url, headers=headers)
    with urllib.request.urlopen(request, timeout=2) as response:
        return json.loads(response.read().decode("utf-8"))


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("binary", type=Path)
    arguments = parser.parse_args()
    binary = arguments.binary.resolve()
    if not binary.is_file():
        raise SystemExit(f"Sidecar binary not found: {binary}")

    port = available_port()
    token = "autocite-sidecar-smoke-token"
    with tempfile.TemporaryDirectory(prefix="autocite-sidecar-smoke-") as temporary:
        database = Path(temporary) / "sessions.sqlite3"
        environment = os.environ.copy()
        environment.update(
            {
                "AUTOCITE_API_TOKEN": token,
                "AUTOCITE_SESSION_DB": str(database),
                "AUTOCITE_APP_QUIET": "1",
                "AUTOCITE_PRINT_TOKEN": "0",
                "PYTHONUTF8": "1",
                "HF_HUB_OFFLINE": "1",
                "TRANSFORMERS_OFFLINE": "1",
            }
        )
        process = subprocess.Popen(
            [str(binary), "--host", "127.0.0.1", "--port", str(port)],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            env=environment,
        )
        try:
            deadline = time.monotonic() + 45
            health: dict[str, object] | None = None
            while time.monotonic() < deadline:
                if process.poll() is not None:
                    stdout, stderr = process.communicate(timeout=2)
                    raise RuntimeError(
                        f"Sidecar exited with {process.returncode}.\nstdout:\n{stdout}\nstderr:\n{stderr}"
                    )
                try:
                    health = request_json(f"http://127.0.0.1:{port}/health")
                    break
                except (OSError, urllib.error.URLError, json.JSONDecodeError):
                    time.sleep(0.25)
            if health is None:
                raise TimeoutError("Sidecar did not become healthy within 45 seconds")
            if health.get("status") != "ok":
                raise RuntimeError(f"Unexpected health response: {health}")

            try:
                request_json(f"http://127.0.0.1:{port}/sessions")
            except urllib.error.HTTPError as error:
                if error.code != 401:
                    raise
            else:
                raise RuntimeError("Protected session endpoint accepted an unauthenticated request")

            sessions = request_json(f"http://127.0.0.1:{port}/sessions", token)
            if not isinstance(sessions.get("sessions"), list):
                raise RuntimeError(f"Unexpected authenticated response: {sessions}")
            print(json.dumps({"health": health, "authenticated": True}, indent=2))
        finally:
            process.terminate()
            try:
                process.wait(timeout=8)
            except subprocess.TimeoutExpired:
                process.kill()
                process.wait(timeout=3)


if __name__ == "__main__":
    main()
