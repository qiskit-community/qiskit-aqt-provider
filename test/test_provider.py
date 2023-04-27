# This code is part of Qiskit.
#
# (C) Copyright IBM 2019, Alpine Quantum Technologies GmbH 2023.
#
# This code is licensed under the Apache License, Version 2.0. You may
# obtain a copy of this license in the LICENSE.txt file in the root directory
# of this source tree or at http://www.apache.org/licenses/LICENSE-2.0.
#
# Any modifications or derivative works of this code must retain this
# copyright notice, and modified files need to carry a notice indicating
# that they have been altered from the originals.


import json
import os
import uuid
from pathlib import Path
from unittest import mock
from urllib.parse import urlparse

import pytest
from pytest_httpx import HTTPXMock

from qiskit_aqt_provider import api_models, api_models_generated
from qiskit_aqt_provider.aqt_provider import OFFLINE_SIMULATORS, AQTProvider


def test_default_portal_url() -> None:
    """Check that by default, the portal url is that of the class variable."""
    with mock.patch.object(os, "environ", {}):
        aqt = AQTProvider("my-token")

    result = urlparse(aqt.portal_url)
    expected = urlparse(AQTProvider.DEFAULT_PORTAL_URL)

    assert result.scheme == expected.scheme
    assert result.netloc == expected.netloc


def test_portal_url_envvar(monkeypatch: pytest.MonkeyPatch) -> None:
    """Check that one can set the portal url via the environment variable."""
    env_url = "https://new-portal.aqt.eu"
    assert env_url != AQTProvider.DEFAULT_PORTAL_URL
    monkeypatch.setenv("AQT_PORTAL_URL", env_url)

    aqt = AQTProvider("my-token")

    result = urlparse(aqt.portal_url)
    expected = urlparse(env_url)

    assert result.scheme == expected.scheme
    assert result.netloc == expected.netloc


def test_access_token_argument() -> None:
    """Check that one can set the access token via the init argument."""
    token = str(uuid.uuid4())
    aqt = AQTProvider(token)
    assert aqt.access_token == token


def test_access_token_envvar(monkeypatch: pytest.MonkeyPatch) -> None:
    """Check that one can set the access token via the environment variable."""
    token = str(uuid.uuid4())
    monkeypatch.setenv("AQT_TOKEN", token)

    aqt = AQTProvider()
    assert aqt.access_token == token


def test_access_token_argument_precendence_over_envvar(monkeypatch: pytest.MonkeyPatch) -> None:
    """Check that the argument has precedence over the environment variable for setting
    the access token.
    """
    arg_token = str(uuid.uuid4())
    env_token = str(uuid.uuid4())
    assert arg_token != env_token

    monkeypatch.setenv("AQT_TOKEN", env_token)

    aqt = AQTProvider(arg_token)
    assert aqt.access_token == arg_token


def test_autoload_env(tmp_path: Path) -> None:
    """Check that the environment variables are loaded from disk by default.

    We don't check the functionality of the python-dotenv library, only that the
    loading call is active by default in `AQTProvider.__init__`.
    """
    env_token = str(uuid.uuid4())
    dotenv_path = tmp_path / "env"
    dotenv_path.write_text(f'AQT_TOKEN = "{env_token}"')

    with mock.patch.object(os, "environ", {}):
        aqt = AQTProvider(dotenv_path=dotenv_path)
        assert aqt.access_token == env_token


def test_autoload_env_deactivated() -> None:
    """Check that auto-loading the environment can be deactivated."""
    with mock.patch.object(os, "environ", {}):
        with pytest.raises(ValueError, match="No access token provided"):
            AQTProvider(load_dotenv=False)


def test_remote_workspaces_table(httpx_mock: HTTPXMock) -> None:
    """Check that the AQTProvider.backends() methods can fetch a list of available
    workspaces and associated resources over HTTP.

    Check that the offline simulators are added if they match the search criteria.
    """
    remote_workspaces = [
        api_models_generated.Workspace(
            id="w1",
            resources=[
                api_models_generated.Resource(
                    id="r1", name="r1", type=api_models_generated.Type.device
                )
            ],
        )
    ]

    httpx_mock.add_response(
        json=json.loads(api_models.Workspaces(__root__=remote_workspaces).json())
    )

    provider = AQTProvider("my-token")

    # List all available backends
    all_backends = provider.backends().by_workspace()
    assert set(all_backends) == {"default", "w1"}
    assert {backend.resource_id for backend in all_backends["w1"]} == {"r1"}
    assert {backend.resource_id for backend in all_backends["default"]} == {
        simulator.id for simulator in OFFLINE_SIMULATORS
    }

    # List only the devices
    only_devices = provider.backends(backend_type="device").by_workspace()
    assert set(only_devices) == {"w1"}
    assert {backend.resource_id for backend in only_devices["w1"]} == {"r1"}

    # List only the offline simulators
    only_offline_simulators = provider.backends(backend_type="offline_simulator").by_workspace()
    assert set(only_offline_simulators) == {"default"}
    assert {backend.resource_id for backend in only_offline_simulators["default"]} == {
        simulator.id for simulator in OFFLINE_SIMULATORS
    }
