# This code is part of Qiskit.
#
# (C) Copyright IBM 2019, Alpine Quantum Technologies 2020
#
# This code is licensed under the Apache License, Version 2.0. You may
# obtain a copy of this license in the LICENSE.txt file in the root directory
# of this source tree or at http://www.apache.org/licenses/LICENSE-2.0.
#
# Any modifications or derivative works of this code must retain this
# copyright notice, and modified files need to carry a notice indicating
# that they have been altered from the originals.


import contextlib
import os
import re
from collections import defaultdict
from dataclasses import dataclass
from operator import attrgetter
from pathlib import Path
from typing import (
    DefaultDict,
    Dict,
    Final,
    List,
    Literal,
    Optional,
    Pattern,
    Sequence,
    Union,
    overload,
)

import dotenv
import httpx
from qiskit.providers import ProviderV1
from tabulate import tabulate
from typing_extensions import TypeAlias

from qiskit_aqt_provider import api_models

from .aqt_resource import AQTResource, OfflineSimulatorResource

StrPath: TypeAlias = Union[str, Path]


@dataclass(frozen=True)
class OfflineSimulator:
    """Description of an offline simulator."""

    id: str
    """Unique identifier of the simulator."""

    name: str
    """Free-text description of the simulator."""

    noisy: bool
    """Whether the simulator uses a noise model."""


OFFLINE_SIMULATORS: Final = [
    OfflineSimulator(id="offline_simulator_no_noise", name="Offline ideal simulator", noisy=False),
]


class BackendsTable(Sequence[AQTResource]):
    """Pretty-printable list of AQT backends."""

    def __init__(self, backends: List[AQTResource]):
        self.backends = backends
        self.headers = ["Workspace ID", "Resource ID", "Description", "Resource type"]

    @overload
    def __getitem__(self, index: int) -> AQTResource:
        ...  # pragma: no cover

    @overload
    def __getitem__(self, index: slice) -> Sequence[AQTResource]:
        ...  # pragma: no cover

    def __getitem__(self, index: Union[slice, int]) -> Union[AQTResource, Sequence[AQTResource]]:
        """Retrieve a backend by index."""
        return self.backends[index]

    def __len__(self) -> int:
        """Number of backends."""
        return len(self.backends)

    def __str__(self) -> str:
        """Text table representation."""
        return tabulate(self.table(), headers=self.headers, tablefmt="fancy_grid")

    def _repr_html_(self) -> str:
        """HTML representation (for IPython)."""
        return tabulate(self.table(), headers=self.headers, tablefmt="html")  # pragma: no cover

    def by_workspace(self) -> Dict[str, List[AQTResource]]:
        """Aggregate backends by workspace."""
        data: DefaultDict[str, List[AQTResource]] = defaultdict(list)

        for backend in self:
            data[backend.workspace_id].append(backend)

        return dict(data)

    def table(self) -> List[List[str]]:
        """Assemble the data for the printable table."""
        table = []
        for workspace_id, resources in self.by_workspace().items():
            for count, resource in enumerate(sorted(resources, key=attrgetter("resource_id"))):
                line = [
                    workspace_id,
                    resource.resource_id,
                    resource.resource_name,
                    resource.resource_type,
                ]
                if count != 0:
                    # don't repeat the workspace id
                    line[0] = ""

                table.append(line)

        return table


class AQTProvider(ProviderV1):
    """Provider for backends from Alpine Quantum Technologies (AQT).

    Typical usage is:

    .. code-block:: python

        >>> from qiskit_aqt_provider import AQTProvider
        ...
        >>> aqt = AQTProvider('MY_TOKEN')
        >>> backend = aqt.get_backend("offline_simulator_no_noise")

    where `'MY_TOKEN'` is the access token provided by AQT.

    If no token is given, it is read from the `AQT_TOKEN` environment variable.
    """

    # Set AQT_PORTAL_URL environment variable to override
    DEFAULT_PORTAL_URL: Final = "http://arnica.internal.aqt.eu"

    def __init__(
        self,
        access_token: Optional[str] = None,
        *,
        load_dotenv: bool = True,
        dotenv_path: Optional[StrPath] = None,
    ):
        """Initialize the AQT provider.

        The access token for the AQT cloud can be provided either through the
        `access_token` argument or the `AQT_TOKEN` environment variable.

        The AQT cloud portal URL can be configured using the `AQT_PORTAL_URL`
        environment variable.

        If `load_dotenv`, environment variables are loaded from a file, by default
        any `.env` file in the working directory or above it in the directory tree.
        The `dotenv_path` argument allows to pass a specific file to load environment
        variables from.

        Args:
            access_token: AQT cloud access token
            load_dotenv: whether to load environment variables from a .env file
            dotenv_path: path to the environment file. This implies `load_dotenv`.
        """
        if load_dotenv or dotenv_path is not None:
            dotenv.load_dotenv(dotenv_path)

        portal_base_url = os.environ.get("AQT_PORTAL_URL", AQTProvider.DEFAULT_PORTAL_URL)
        self.portal_url = f"{portal_base_url}/api/v1"

        if access_token is None:
            env_token = os.environ.get("AQT_TOKEN")
            if env_token is None:
                raise ValueError("No access token provided. Use 'AQT_TOKEN' environment variable.")
            self.access_token = env_token
        else:
            self.access_token = access_token
        self.name = "aqt_provider"

    @property
    def _http_client(self) -> httpx.Client:
        """HTTP client for communicating with the AQT cloud service."""
        return api_models.http_client(base_url=self.portal_url, token=self.access_token)

    def backends(
        self,
        name: Optional[Union[str, Pattern[str]]] = None,
        *,
        backend_type: Optional[Literal["device", "simulator", "offline_simulator"]] = None,
        workspace: Optional[Union[str, Pattern[str]]] = None,
    ) -> BackendsTable:
        """Search for backends matching given criteria.

        With no arguments, return all backends accessible with the configured
        access token.

        Args:
            name: regular expression pattern for the resource ID
            backend_type: whether to search for simulators or hardware devices
            workspace: regular expression for the workspace ID.

        Returns:
            List of backends accessible with the given access token that match the
            given criteria.
        """
        remote_workspaces = api_models.Workspaces(__root__=[])

        if backend_type != "offline_simulator":
            with contextlib.suppress(httpx.HTTPError, httpx.NetworkError):
                with self._http_client as client:
                    resp = client.get("/workspaces")
                    resp.raise_for_status()

                remote_workspaces = api_models.Workspaces.parse_obj(resp.json()).filter(
                    name_pattern=name,
                    backend_type=api_models.ResourceType(backend_type) if backend_type else None,
                    workspace_pattern=workspace,
                )

        backends: List[AQTResource] = []

        # add offline simulators in the default workspace
        if (not workspace or re.match(workspace, "default", re.IGNORECASE)) and (
            not backend_type or backend_type == "offline_simulator"
        ):
            for simulator in OFFLINE_SIMULATORS:
                if name and not re.match(name, simulator.id, re.IGNORECASE):
                    continue
                backends.append(
                    OfflineSimulatorResource(
                        self,
                        workspace_id="default",
                        resource_id=simulator.id,
                        resource_name=simulator.name,
                        noisy=simulator.noisy,
                    )
                )

        # add (filtered) remote resources
        for _workspace in remote_workspaces.__root__:
            for resource in _workspace.resources:
                backends.append(
                    AQTResource(
                        self,
                        workspace_id=_workspace.id,
                        resource_id=resource.id,
                        resource_name=resource.name,
                        resource_type=resource.type.value,
                    )
                )

        return BackendsTable(backends)
