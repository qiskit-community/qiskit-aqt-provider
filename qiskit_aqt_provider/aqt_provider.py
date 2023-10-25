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
import warnings
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
from typing_extensions import TypeAlias, override

from qiskit_aqt_provider import api_models

from .aqt_resource import AQTResource, OfflineSimulatorResource

StrPath: TypeAlias = Union[str, Path]


class NoTokenWarning(UserWarning):
    """Warning emitted when a provider is initialized with no access token."""


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
    OfflineSimulator(id="offline_simulator_noise", name="Offline noisy simulator", noisy=True),
]


class BackendsTable(Sequence[AQTResource]):
    """Pretty-printable collection of AQT backends.

    The :meth:`__str__` method returns a plain text table reprensentation of the available backends.
    The :meth:`_repr_html_` method returns an HTML representation that is automatically used
    in IPython/Jupyter notebooks.
    """

    def __init__(self, backends: List[AQTResource]):
        self.backends = backends
        self.headers = ["Workspace ID", "Resource ID", "Description", "Resource type"]

    @overload
    def __getitem__(self, index: int) -> AQTResource:
        ...  # pragma: no cover

    @overload
    def __getitem__(self, index: slice) -> Sequence[AQTResource]:
        ...  # pragma: no cover

    @override
    def __getitem__(self, index: Union[slice, int]) -> Union[AQTResource, Sequence[AQTResource]]:
        """Retrieve a backend by index."""
        return self.backends[index]

    @override
    def __len__(self) -> int:
        """Number of backends."""
        return len(self.backends)

    @override
    def __str__(self) -> str:
        """Plain-text table representation."""
        return tabulate(self.table(), headers=self.headers, tablefmt="fancy_grid")

    def _repr_html_(self) -> str:
        """HTML table representation (for IPython/Jupyter)."""
        return tabulate(self.table(), headers=self.headers, tablefmt="html")  # pragma: no cover

    def by_workspace(self) -> Dict[str, List[AQTResource]]:
        """Backends grouped by workspace ID."""
        data: DefaultDict[str, List[AQTResource]] = defaultdict(list)

        for backend in self:
            data[backend.resource_id.workspace_id].append(backend)

        return dict(data)

    def table(self) -> List[List[str]]:
        """Assemble the data for the printable table."""
        table = []
        for workspace_id, resources in self.by_workspace().items():
            for count, resource in enumerate(
                sorted(resources, key=attrgetter("resource_id.resource_id"))
            ):
                line = [
                    workspace_id,
                    resource.resource_id.resource_id,
                    resource.resource_id.resource_name,
                    resource.resource_id.resource_type,
                ]
                if count != 0:
                    # don't repeat the workspace id
                    line[0] = ""

                table.append(line)

        return table


class AQTProvider(ProviderV1):
    """Provider for backends from Alpine Quantum Technologies (AQT)."""

    # Set AQT_PORTAL_URL environment variable to override
    DEFAULT_PORTAL_URL: Final = "https://arnica-stage.aqt.eu"

    def __init__(
        self,
        access_token: Optional[str] = None,
        *,
        load_dotenv: bool = True,
        dotenv_path: Optional[StrPath] = None,
    ):
        """Initialize the AQT provider.

        The access token for the AQT cloud can be provided either through the
        ``access_token`` argument or the ``AQT_TOKEN`` environment variable.

        .. hint:: If no token is set (neither through the ``access_token`` argument nor
            through the ``AQT_TOKEN`` environment variable), the provider is initialized
            with access to the offline simulators only and :class:`NoTokenWarning` is
            emitted.

        The AQT cloud portal URL can be configured using the ``AQT_PORTAL_URL``
        environment variable.

        If ``load_dotenv`` is true, environment variables are loaded from a file,
        by default any ``.env`` file in the working directory or above it in the
        directory tree.
        The ``dotenv_path`` argument allows to pass a specific file to load environment
        variables from.

        Args:
            access_token: AQT cloud access token.
            load_dotenv: whether to load environment variables from a ``.env`` file.
            dotenv_path: path to the environment file. This implies ``load_dotenv``.
        """
        if load_dotenv or dotenv_path is not None:
            dotenv.load_dotenv(dotenv_path)

        portal_base_url = os.environ.get("AQT_PORTAL_URL", AQTProvider.DEFAULT_PORTAL_URL)
        self.portal_url = f"{portal_base_url}/api/v1"

        if access_token is None:
            self.access_token = os.environ.get("AQT_TOKEN", "")
        else:
            self.access_token = access_token

        if not self.access_token:
            warnings.warn(
                "No access token provided: access is restricted to the 'default' workspace.",
                NoTokenWarning,
            )

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

        Filters can be either strings or regular expression patterns. Strings filter by
        exact match.

        Args:
            name: filter for the backend name.
            backend_type: if given, restrict the search to the given backend type.
            workspace: filter for the workspace ID.

        Returns:
            Collection of backends accessible with the given access token that match the
            given criteria.
        """
        if isinstance(name, str):
            name = re.compile(f"^{name}$")

        if isinstance(workspace, str):
            workspace = re.compile(f"^{workspace}$")

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
        if (not workspace or workspace.match("default")) and (
            not backend_type or backend_type == "offline_simulator"
        ):
            for simulator in OFFLINE_SIMULATORS:
                if name and not name.match(simulator.id):
                    continue
                backends.append(
                    OfflineSimulatorResource(
                        self,
                        resource_id=api_models.ResourceId(
                            workspace_id="default",
                            resource_id=simulator.id,
                            resource_name=simulator.name,
                            resource_type="offline_simulator",
                        ),
                        with_noise_model=simulator.noisy,
                    )
                )

        # add (filtered) remote resources
        for _workspace in remote_workspaces.__root__:
            for resource in _workspace.resources:
                backends.append(
                    AQTResource(
                        self,
                        resource_id=api_models.ResourceId(
                            workspace_id=_workspace.id,
                            resource_id=resource.id,
                            resource_name=resource.name,
                            resource_type=resource.type.value,
                        ),
                    )
                )

        return BackendsTable(backends)
