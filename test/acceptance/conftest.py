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
        except Exception as e:  # noqa: BLE001
            print(e)  # noqa: T201
        time.sleep(0.05)
    return False


class DummyArnicaServer:
    """Fixture for interacting with the dummy server that implements the cloud API."""

    def __init__(self, base_url: str, client: httpx.Client) -> None:
        self.base_url = base_url
        self.client = client

    def get_recorded_requests(self) -> list[Any]:
        """Fetches the requests recorded by the dummy server."""
        response = self.client.get("/__requests")
        response.raise_for_status()
        return list(response.json())

    def clear_recorded_requests(self) -> None:
        """Clears the requests recorded by the dummy server."""
        response = self.client.post("/__clear")
        response.raise_for_status()


class DummyDirectAccessServer:
    """Fixture for interacting with the dummy server that implements the direct access API."""

    def __init__(self, base_url: str, client: httpx.Client) -> None:
        self.base_url = base_url
        self.client = client

    def get_recorded_requests(self) -> list[Any]:
        """Fetches the requests recorded by the dummy server."""
        response = self.client.get("/__requests")
        response.raise_for_status()
        return list(response.json())

    def clear_recorded_requests(self) -> None:
        """Clears the requests recorded by the dummy server."""
        response = self.client.post("/__clear")
        response.raise_for_status()

    def reset_direct_access(self) -> None:
        """Resets the state of the dummy direct access server."""
        response = self.client.post("/__direct/reset")
        response.raise_for_status()

    def configure_direct_access(self, **config: Any) -> None:
        """Configures the dummy direct access server with the given settings."""
        response = self.client.post("/__direct/config", json=config)
        response.raise_for_status()


def _spawn_dummy_server(entrypoint: str) -> tuple[subprocess.Popen[bytes], str]:
    port = _get_free_port()
    env = os.environ.copy()
    env["PYTHONUNBUFFERED"] = "1"
    cmd = [
        sys.executable,
        "-m",
        "fastapi",
        "run",
        "--entrypoint",
        entrypoint,
        "--host",
        "127.0.0.1",
        "--port",
        str(port),
    ]
    process = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, env=env)  # noqa: S603
    base_url = f"http://127.0.0.1:{port}"
    if not _wait_for(f"{base_url}/health", timeout=8.0):
        process.kill()
        out, err = process.communicate(timeout=1)
        raise RuntimeError(f"Test server failed to start\nstdout:{out.decode()}\nstderr:{err.decode()}")

    return process, base_url


@pytest.fixture(scope="session")
def dummy_cloud_server() -> Generator[DummyArnicaServer, None, None]:
    """Starts a dummy server that implements the cloud API and yields a fixture for interacting with it."""
    process, base_url = _spawn_dummy_server("test.acceptance.support.dummy_cloud_api:app")

    with httpx.Client(base_url=base_url) as client:
        fixture = DummyArnicaServer(
            base_url,
            client,
        )
        yield fixture

    # shutdown
    try:
        process.send_signal(signal.SIGINT)
        process.wait(timeout=3)
    except Exception:  # noqa: BLE001
        process.kill()
        process.wait()


@pytest.fixture(scope="session")
def dummy_direct_access_server() -> Generator[DummyDirectAccessServer, None, None]:
    """Starts a dummy server that implements the direct access API and yields a fixture for interacting with it.

    Prefer using the `direct_access_api` fixture in tests, which depends on this fixture and ensures that the server
    state is reset before each test.
    """
    process, base_url = _spawn_dummy_server("test.acceptance.support.dummy_direct_access_api:app")

    with httpx.Client(base_url=base_url) as client:
        fixture = DummyDirectAccessServer(base_url, client)
        fixture.reset_direct_access()
        fixture.clear_recorded_requests()
        yield fixture

    # shutdown
    try:
        process.send_signal(signal.SIGINT)
        process.wait(timeout=3)
    except Exception:  # noqa: BLE001
        process.kill()
        process.wait()


@pytest.fixture(name="direct_access_api")
def clear_server_state(dummy_direct_access_server: DummyDirectAccessServer) -> DummyDirectAccessServer:
    """Clears the state of the dummy direct access server before each test."""
    dummy_direct_access_server.reset_direct_access()
    dummy_direct_access_server.clear_recorded_requests()
    return dummy_direct_access_server
