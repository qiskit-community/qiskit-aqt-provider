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


import itertools
import os
from pathlib import Path
from typing import Dict, Final, Iterable, Iterator, List, Optional, Set, Union

import dotenv
import httpx
from qiskit.providers.exceptions import QiskitBackendNotFoundError
from tabulate import tabulate
from typing_extensions import NotRequired, TypeAlias, TypedDict

from .aqt_resource import ApiResource, AQTResource, OfflineSimulatorResource
from .constants import REQUESTS_TIMEOUT

StrPath: TypeAlias = Union[str, Path]


class WorkspaceResources(TypedDict):
    """Return type of the '/workspaces' endpoint on the AQT public API."""

    id: NotRequired[str]
    """Workspace identifier."""

    resources: NotRequired[List[ApiResource]]
    """List of resources for that workspace."""


class WorkspaceTable:
    """Pretty-printable list of workspaces and associated resources."""

    class OfflineSimulators:
        """Identifiers for the offline simulators, available in any workspace."""

        NO_NOISE: Final = ("offline_simulator_no_noise", "Offline ideal simulator")

        @classmethod
        def resources(cls) -> Iterator[ApiResource]:
            """Offline simulator resources."""
            for key in vars(cls):
                if not key.startswith("__") and key != "resources":
                    resource_id, resource_name = getattr(cls, key)
                    yield ApiResource(id=resource_id, name=resource_name, type="offline_simulator")

    def __init__(self, data: Iterable[WorkspaceResources]):
        self._workspaces: Dict[str, List[ApiResource]] = {}

        for entry in data:
            workspace_id = entry.get("id")
            if workspace_id is None:
                continue
            resources = entry.get("resources", [])
            self._workspaces[workspace_id] = list(
                itertools.chain(WorkspaceTable.OfflineSimulators.resources(), resources)
            )

        # if no workspace is available online, provide a default one
        # with the offline simulators.
        if not self._workspaces:
            self._workspaces["default"] = list(WorkspaceTable.OfflineSimulators.resources())

        self.headers = ["Workspace ID", "Resource ID", "Description", "Resource type"]
        self.table = []
        for workspace_id, resources in self._workspaces.items():
            for count, resource in enumerate(resources):
                if count == 0:
                    line = [
                        workspace_id,
                        resource["id"],
                        resource["name"],
                        resource["type"],
                    ]
                else:
                    line = ["", resource["id"], resource["name"], resource["type"]]
                self.table.append(line)

    def workspaces(self) -> Set[str]:
        """Names of the available workspaces names."""
        return set(self._workspaces.keys())

    def workspace(self, workspace_id: str) -> List[ApiResource]:
        """List of resources in a given workspace."""
        return self._workspaces.get(workspace_id, [])

    def __str__(self) -> str:
        """Text table representation."""
        return tabulate(self.table, headers=self.headers, tablefmt="fancy_grid")

    def _repr_html_(self) -> str:
        """HTML representation (for IPython)."""
        return tabulate(self.table, headers=self.headers, tablefmt="html")


class AQTProvider:
    """Provider for backends from Alpine Quantum Technologies (AQT).

    Typical usage is:

    .. code-block:: python

        >>> from qiskit_aqt_provider import AQTProvider
        ...
        >>> aqt = AQTProvider('MY_TOKEN')
        >>> backend = aqt.get_resource("default", "offline_simulator_no_noise")

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

    def workspaces(self) -> WorkspaceTable:
        """Pretty-printable list of workspaces and accessible resources."""
        if os.environ.get("CI"):
            # don't attempt to connect to the AQT Arnica service when running CI tests
            return WorkspaceTable([])

        headers = {"Authorization": f"Bearer {self.access_token}", "SDK": "qiskit"}
        try:
            res = httpx.get(
                f"{self.portal_url}/workspaces", headers=headers, timeout=REQUESTS_TIMEOUT
            )
            res.raise_for_status()
            return WorkspaceTable(res.json())
        except (httpx.HTTPError, httpx.NetworkError):
            return WorkspaceTable([])

    def get_resource(self, workspace: str, resource: str) -> AQTResource:
        """Retrieve a resource (Qiskit backend) from a workspace.

        Args:
            workspace: name of the workspace for the resource lookup
            resource: name of the resource to retrieve.

        Returns:
            A Qiskit backend for running jobs on the target resource.

        Raises:
            QiskitBackendNotFound: the workspace or the resource are not accessible.
        """
        resources = self.workspaces().workspace(workspace)
        if not resources:
            raise QiskitBackendNotFoundError(f"Workpace '{workspace}' is not accessible.")

        api_resource = None
        for resource_data in resources:
            if resource_data.get("id") == resource:
                api_resource = resource_data
                break
        else:
            raise QiskitBackendNotFoundError(
                f"Resource '{resource}' does not exist in workspace '{workspace}'."
            )

        resource_class = (
            OfflineSimulatorResource if api_resource["type"] == "offline_simulator" else AQTResource
        )
        return resource_class(self, workspace, api_resource)
