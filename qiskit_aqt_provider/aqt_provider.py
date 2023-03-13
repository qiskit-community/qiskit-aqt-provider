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
from typing import Dict, Final, Iterable, Iterator, List, Optional, Set

import requests
from qiskit.providers.exceptions import QiskitBackendNotFoundError
from qiskit.providers.providerutils import filter_backends
from tabulate import tabulate
from typing_extensions import NotRequired, TypedDict

from .aqt_backend import AQTDeviceIbex, AQTDevicePine, AQTSimulator, AQTSimulatorNoise1
from .aqt_resource import ApiResource, AQTResource, OfflineSimulatorResource
from .constants import REQUESTS_TIMEOUT

# The portal url can be overridden via the AQT_PORTAL_URL environment variable

# Firebase Arnica
# PORTAL_URL = "https://europe-west3-aqt-portal-dev.cloudfunctions.net"

# Arnica MVP
PORTAL_URL = "http://arnica.internal.aqt.eu:7777"

# Local Firebase Arnica
# PORTAL_URL = "http://localhost:5001/aqt-portal-dev/europe-west3"

# Local mini portal
# PORTAL_URL = "http://localhost:7777"


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
                    yield ApiResource(
                        {"id": resource_id, "name": resource_name, "type": "offline_simulator"}
                    )

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
        return tabulate(self.table, headers=self.headers, tablefmt="fancy_grid")

    def _repr_html_(self) -> str:
        """HTML representation (for IPython)."""
        return tabulate(self.table, headers=self.headers, tablefmt="html")

    def __iter__(self):
        return self._workspaces.__iter__()


class AQTProvider:
    """Provider for backends from Alpine Quantum Technologies (AQT).

    Typical usage is:

    .. code-block:: python

        from qiskit_aqt_provider import AQTProvider

        aqt = AQTProvider('MY_TOKEN')

        backend = aqt.backends.aqt_qasm_simulator

    where `'MY_TOKEN'` is the access token provided by AQT.

    If no token is given, it is read from the `AQT_TOKEN` environment variable.

    Attributes:
        access_token (str): The access token.
        name (str): Name of the provider instance.
        backends (BackendService): A service instance that allows
                                   for grabbing backends.
    """

    def __init__(self, access_token: Optional[str] = None):
        super().__init__()
        portal_url_env = os.environ.get("AQT_PORTAL_URL")
        if portal_url_env:
            self.portal_url = f"{portal_url_env}/api/v1"
        else:
            self.portal_url = f"{PORTAL_URL}/api/v1"
        if access_token is None:
            env_token = os.environ.get("AQT_TOKEN")
            if env_token is None:
                raise ValueError("No access token provided. Use 'AQT_TOKEN' environment variable.")
            self.access_token = env_token
        else:
            self.access_token = access_token
        self.name = "aqt_provider"

        # Populate the list of AQT backends
        self.backends = BackendService(
            [
                AQTSimulator(provider=self),
                AQTSimulatorNoise1(provider=self),
                AQTDeviceIbex(provider=self),
                AQTDevicePine(provider=self),
            ]
        )

    def __str__(self):
        return f"<AQTProvider(name={self.name})>"

    def __repr__(self):
        return self.__str__()

    def workspaces(self) -> WorkspaceTable:
        """Pretty-printable list of workspaces and accessible resources."""
        if os.environ.get("CI"):
            # don't attempt to connect to the AQT Arnica service when running CI tests
            return WorkspaceTable([])

        headers = {"Authorization": f"Bearer {self.access_token}", "SDK": "qiskit"}
        try:
            res = requests.get(
                f"{self.portal_url}/workspaces", headers=headers, timeout=REQUESTS_TIMEOUT
            )
            res.raise_for_status()
            return WorkspaceTable(res.json())
        except (requests.HTTPError, requests.ConnectionError):
            return WorkspaceTable([])

    def get_resource(self, workspace: str, resource: str) -> AQTResource:
        """Retrieve a resource (Qiskit backend) from a workspace.

        Args:
            workspace: name of the workspace for the resource lookup
            resource: name of the resource to retrieve.

        Returns:
            A Qiskit backend for running jobs on the target resource.

        Raises:
            ValueError: the workspace or the resource are not accessible.
        """
        resources = self.workspaces().workspace(workspace)
        if not resources:
            raise ValueError(f"Workpace '{workspace}' is not accessible.")

        api_resource = None
        for resource_data in resources:
            if resource_data.get("id") == resource:
                api_resource = resource_data
                break
        else:
            raise ValueError(f"Resource '{resource}' does not exist in workspace '{workspace}'.")

        resource_class = (
            OfflineSimulatorResource if api_resource["type"] == "offline_simulator" else AQTResource
        )
        return resource_class(self, workspace, api_resource)

    def get_backend(self, name=None, **kwargs):
        """Return a single backend matching the specified filtering.
        Args:
            name (str): name of the backend.
            **kwargs: dict used for filtering.
        Returns:
            Backend: a backend matching the filtering.
        Raises:
            QiskitBackendNotFoundError: if no backend could be found or
                more than one backend matches the filtering criteria.
        """
        backends = self.backends(name, **kwargs)
        if len(backends) > 1:
            raise QiskitBackendNotFoundError("More than one backend matches criteria.")
        if not backends:
            raise QiskitBackendNotFoundError("No backend matches criteria.")

        return backends[0]

    def __eq__(self, other):
        """Equality comparison.
        By default, it is assumed that two `Providers` from the same class are
        equal. Subclassed providers can override this behavior.
        """
        return type(self).__name__ == type(other).__name__


class BackendService:
    """A service class that allows for autocompletion
    of backends from provider.
    """

    def __init__(self, backends):
        """Initialize service

        Parameters:
            backends (list): List of backend instances.
        """
        self._backends = backends
        for backend in backends:
            setattr(self, backend.name, backend)

    def __call__(self, name=None, filters=None, **kwargs):
        """A listing of all backends from this provider.

        Parameters:
            name (str): The name of a given backend.
            filters (callable): A filter function.

        Returns:
            list: A list of backends, if any.
        """
        # pylint: disable=arguments-differ
        backends = self._backends
        if name:
            backends = [backend for backend in backends if backend.name == name]

        return filter_backends(backends, filters=filters, **kwargs)
