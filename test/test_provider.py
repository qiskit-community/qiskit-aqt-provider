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
import re
import uuid
from pathlib import Path
from typing import Optional
from unittest import mock

import httpx
import pytest
from pytest_httpx import HTTPXMock
from qiskit.exceptions import QiskitError

from qiskit_aqt_provider.api_client import DEFAULT_PORTAL_URL
from qiskit_aqt_provider.api_client import models as api_models
from qiskit_aqt_provider.api_client import models_direct as api_models_direct
from qiskit_aqt_provider.api_client import models_generated as api_models_generated
from qiskit_aqt_provider.aqt_provider import OFFLINE_SIMULATORS, AQTProvider, NoTokenWarning
from qiskit_aqt_provider.test.resources import DummyDirectAccessResource


def test_default_portal_url() -> None:
    """Check that by default, the portal url is that of the class variable."""
    with mock.patch.object(os, "environ", {}):
        aqt = AQTProvider("my-token")

    assert aqt._portal_client.portal_url == DEFAULT_PORTAL_URL


def test_portal_url_envvar(monkeypatch: pytest.MonkeyPatch) -> None:
    """Check that one can set the portal url via the environment variable."""
    env_url = httpx.URL("https://new-portal.aqt.eu")
    assert env_url != DEFAULT_PORTAL_URL
    monkeypatch.setenv("AQT_PORTAL_URL", str(env_url))

    aqt = AQTProvider("my-token")

    assert aqt._portal_client.portal_url == env_url


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


def test_access_token_argument_precedence_over_envvar(monkeypatch: pytest.MonkeyPatch) -> None:
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


def test_default_to_empty_token() -> None:
    """Check that if no token is passed and AQT_TOKEN is not found in the environment,
    the access token is set to an empty string.

    In this case, the only accessible workspace is the default workspace.
    """
    with mock.patch.object(os, "environ", {}):
        with pytest.warns(NoTokenWarning, match="No access token provided"):
            aqt = AQTProvider(load_dotenv=False)

        assert aqt.access_token == ""

    assert list(aqt.backends().by_workspace()) == ["default"]


@pytest.mark.httpx_mock(can_send_already_matched_responses=True)
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
        url=re.compile(".+/workspaces$"),
        json=json.loads(api_models.ApiWorkspaces(root=remote_workspaces).model_dump_json()),
    )

    httpx_mock.add_callback(sample_resource_details, url=re.compile(".+/resources/.+"))

    provider = AQTProvider("my-token")

    # List all available backends
    all_backends = provider.backends().by_workspace()
    assert set(all_backends) == {"default", "w1"}
    assert {backend.resource_id.resource_id for backend in all_backends["w1"]} == {"r1"}
    assert {backend.resource_id.resource_id for backend in all_backends["default"]} == {
        simulator.id for simulator in OFFLINE_SIMULATORS
    }

    # List only the devices
    only_devices = provider.backends(backend_type="device").by_workspace()
    assert set(only_devices) == {"w1"}
    assert {backend.resource_id.resource_id for backend in only_devices["w1"]} == {"r1"}

    # List only the offline simulators
    only_offline_simulators = provider.backends(backend_type="offline_simulator").by_workspace()
    assert set(only_offline_simulators) == {"default"}
    assert {backend.resource_id.resource_id for backend in only_offline_simulators["default"]} == {
        simulator.id for simulator in OFFLINE_SIMULATORS
    }


@pytest.mark.httpx_mock(can_send_already_matched_responses=True)
def test_remote_workspaces_filtering_prefix_collision(httpx_mock: HTTPXMock) -> None:
    """Check the string and pattern variants of filters in AQTProvider.backends.

    Use two workspaces with one device each, where both workspaces and devices have
    the same prefix. Check that passing a string as filter requires an exact match,
    while passing a pattern matches according to the pattern.
    """
    remote_workspaces = [
        api_models_generated.Workspace(
            id="workspace",
            resources=[
                api_models_generated.Resource(
                    id="foo", name="foo", type=api_models_generated.Type.device
                ),
            ],
        ),
        api_models_generated.Workspace(
            id="workspace_extra",
            resources=[
                api_models_generated.Resource(
                    id="foo-extra", name="foo-extra", type=api_models_generated.Type.device
                ),
            ],
        ),
    ]

    httpx_mock.add_response(
        url=re.compile(".+/workspaces$"),
        json=json.loads(api_models.ApiWorkspaces(root=remote_workspaces).model_dump_json()),
    )

    httpx_mock.add_callback(sample_resource_details, url=re.compile(".+/resources/.+"))

    provider = AQTProvider("my-token")

    # with exact match on workspace
    only_base = provider.backends(workspace="workspace").by_workspace()
    assert set(only_base) == {"workspace"}
    assert {backend.resource_id.resource_id for backend in only_base["workspace"]} == {"foo"}

    # with strict pattern on workspace
    only_base = provider.backends(workspace=re.compile("^workspace$")).by_workspace()
    assert set(only_base) == {"workspace"}
    assert {backend.resource_id.resource_id for backend in only_base["workspace"]} == {"foo"}

    # with permissive pattern on workspace
    both_ws = provider.backends(workspace=re.compile("workspace")).by_workspace()
    assert set(both_ws) == {"workspace", "workspace_extra"}
    assert {
        backend.resource_id.resource_id
        for workspace in ("workspace", "workspace_extra")
        for backend in both_ws[workspace]
    } == {"foo", "foo-extra"}

    # with exact match on name
    only_base = provider.backends(name="foo").by_workspace()
    assert set(only_base) == {"workspace"}
    assert {backend.resource_id.resource_id for backend in only_base["workspace"]} == {"foo"}

    # with strict pattern on name
    only_base = provider.backends(name=re.compile("^foo$")).by_workspace()
    assert set(only_base) == {"workspace"}
    assert {backend.resource_id.resource_id for backend in only_base["workspace"]} == {"foo"}

    # with permissive pattern on name
    both_ws = provider.backends(name=re.compile("foo")).by_workspace()
    assert set(both_ws) == {"workspace", "workspace_extra"}
    assert {
        backend.resource_id.resource_id
        for workspace in ("workspace", "workspace_extra")
        for backend in both_ws[workspace]
    } == {"foo", "foo-extra"}


def test_remote_resource_target_matches_available_qubits(httpx_mock: HTTPXMock) -> None:
    """Check that the remote resources' targets have the expected number of qubits.

    When enumerating devices, the provider also fetches the number of qubits available
    per device. This value is used to configure the transpilation target for that device.
    """
    available_qubits = 42

    remote_workspaces = [
        api_models_generated.Workspace(
            id="w1",
            resources=[
                api_models_generated.Resource(
                    id="r1", name="r1-name", type=api_models_generated.Type.device
                )
            ],
        )
    ]

    httpx_mock.add_response(
        url=re.compile(".+/workspaces$"),
        json=json.loads(api_models.ApiWorkspaces(root=remote_workspaces).model_dump_json()),
    )

    httpx_mock.add_response(
        url=re.compile(".+/resources/r1$"),
        json=json.loads(
            api_models_generated.ResourceDetails(
                id="r1",
                name="r1_name",
                status=api_models_generated.ResourceStates.online,
                type=api_models_generated.Type.device,
                available_qubits=available_qubits,
            ).model_dump_json()
        ),
    )

    provider = AQTProvider("my-token")

    # There's only one resource in workspace w1.
    resource = provider.backends().by_workspace()["w1"][0]
    assert resource.target.num_qubits == available_qubits


def test_direct_access_resource_target_matches_available_qubits(httpx_mock: HTTPXMock) -> None:
    """Check that the direct-access resources' targets have the expected number of qubits.

    When initializing direct-access devices, we fetch the number of available qubits.
    This value is used to configure the transpilation target for that device.

    This is a *resource* test but is placed in this module since it mirrors the one above
    that checks the same property for remote devices.
    """
    available_qubits = 24

    httpx_mock.add_response(
        json=json.loads(api_models_direct.NumIons(num_ions=available_qubits).model_dump_json()),
        url=re.compile(".+/status/ions"),
    )

    assert DummyDirectAccessResource("token").target.num_qubits == available_qubits


@pytest.mark.parametrize("available_qubits", [None, 32])
def test_offline_simulator_set_qubits(available_qubits: Optional[int]) -> None:
    """Check that one can configure the offline simulators' number of qubits in `get_backend()`."""
    provider = AQTProvider("my-token")
    backend = provider.get_backend("offline_simulator_no_noise", available_qubits=available_qubits)

    # 20 is the default number of qubits for the offline simulators
    assert backend.target.num_qubits == available_qubits if available_qubits is not None else 20


@pytest.mark.parametrize("try_set_qubits", [False, True])
def test_cannot_set_qubits_for_remote_resource(try_set_qubits: bool, httpx_mock: HTTPXMock) -> None:
    """Check that `get_backend(available_qubits=...)` is not valid for remote resources."""
    remote_workspaces = [
        api_models_generated.Workspace(
            id="w1",
            resources=[
                api_models_generated.Resource(
                    id="r1", name="r1-name", type=api_models_generated.Type.device
                )
            ],
        )
    ]

    httpx_mock.add_response(
        url=re.compile(".+/workspaces$"),
        json=json.loads(api_models.ApiWorkspaces(root=remote_workspaces).model_dump_json()),
    )

    httpx_mock.add_response(
        url=re.compile(".+/resources/r1$"),
        json=json.loads(
            api_models_generated.ResourceDetails(
                id="r1",
                name="r1_name",
                status=api_models_generated.ResourceStates.online,
                type=api_models_generated.Type.device,
                available_qubits=123,
            ).model_dump_json()
        ),
    )

    provider = AQTProvider("my-token")

    if try_set_qubits:
        with pytest.raises(QiskitError, match=r"available_qubits"):
            backend = provider.get_backend("r1", available_qubits=321)
    else:
        backend = provider.get_backend("r1")
        assert backend.target.num_qubits == 123


def sample_resource_details(request: httpx.Request) -> httpx.Response:
    """Mock response for the `GET /resources/<resource_id>` query.

    Return details for an online remote device with 20 qubits.
    """
    _, resource_id = request.url.path.rstrip("/").rsplit("/", maxsplit=1)

    return httpx.Response(
        status_code=httpx.codes.OK,
        json=json.loads(
            api_models_generated.ResourceDetails(
                id=resource_id,
                name=resource_id,
                status=api_models_generated.ResourceStates.online,
                type=api_models_generated.Type.device,
                available_qubits=20,
            ).model_dump_json()
        ),
    )
