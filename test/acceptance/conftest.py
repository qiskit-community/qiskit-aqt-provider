import os
import signal
import socket
import subprocess
import sys
import time
from collections.abc import Generator
from typing import Any

import httpx
import pytest
import requests


def _get_free_port() -> int:
    s = socket.socket()
    s.bind(("", 0))
    port = s.getsockname()[1]
    s.close()
    return int(port)


def _wait_for(url: str, timeout: float = 5.0) -> bool:
    deadline = time.time() + timeout
    while time.time() < deadline:
        try:
            r = requests.get(url, timeout=0.5)
            if r.status_code == 200:
                return True
        except Exception:
            pass
        time.sleep(0.05)
    return False


class DummyArnicaServer:
    def __init__(self, base_url: str, client: httpx.Client) -> None:
        self.base_url = base_url
        self.client = client

    def get_recorded_requests(self) -> list[Any]:
        response = self.client.get("/__requests")
        response.raise_for_status()
        return list(response.json())


@pytest.fixture(scope="session")
def dummy_server() -> Generator[DummyArnicaServer, None, None]:
    port = _get_free_port()
    env = os.environ.copy()
    env["PYTHONUNBUFFERED"] = "1"
    cmd = [
        sys.executable,
        "-m",
        "fastapi",
        "run",
        "--entrypoint",
        "test.acceptance.support.dummy_api:app",
        "--host",
        "127.0.0.1",
        "--port",
        str(port),
    ]
    p = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, env=env)
    base_url = f"http://127.0.0.1:{port}"
    if not _wait_for(f"{base_url}/health", timeout=8.0):
        p.kill()
        out, err = p.communicate(timeout=1)
        raise RuntimeError(f"Test server failed to start\nstdout:{out.decode()}\nstderr:{err.decode()}")

    with httpx.Client(base_url=base_url) as client:
        fixture = DummyArnicaServer(
            base_url,
            client,
        )
        yield fixture

    # shutdown
    try:
        p.send_signal(signal.SIGINT)
        p.wait(timeout=3)
    except Exception:
        p.kill()
        p.wait()
