# This code is part of Qiskit.
#
# (C) Copyright IBM 2019.
#
# This code is licensed under the Apache License, Version 2.0. You may
# obtain a copy of this license in the LICENSE.txt file in the root directory
# of this source tree or at http://www.apache.org/licenses/LICENSE-2.0.
#
# Any modifications or derivative works of this code must retain this
# copyright notice, and modified files need to carry a notice indicating
# that they have been altered from the originals.


import os
from http import HTTPStatus
from typing import Dict, List, Optional, Union

import requests
from qiskit.providers.exceptions import QiskitBackendNotFoundError
from qiskit.providers.providerutils import filter_backends
from tabulate import tabulate

from .aqt_backend import AQTDeviceIbex, AQTDevicePine, AQTSimulator, AQTSimulatorNoise1
from .aqt_resource import AQTResource
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


class WorkspaceTable:
    def __init__(self, data):
        self.data: Dict[str, List] = {}
        for entry in data:
            workspace_id = entry.get("id")
            resources = entry.get("resources")
            self.data[workspace_id] = resources

        self.table = []
        for workspace_id, resources in self.data.items():
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

    def workspace(self, workspace_id: str) -> Union[List, None]:
        return self.data.get(workspace_id)

    def __str__(self) -> str:
        headers = ["Workspace ID", "Resource ID", "Description", "Resource type"]
        return tabulate(self.table, headers=headers, tablefmt="fancy_grid")

    def __iter__(self):
        return self.data.__iter__()


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

    def workspaces(self):
        headers = {"Authorization": f"Bearer {self.access_token}", "SDK": "qiskit"}
        res = requests.get(
            f"{self.portal_url}/workspaces", headers=headers, timeout=REQUESTS_TIMEOUT
        )
        if res.status_code == HTTPStatus.OK:
            return WorkspaceTable(res.json())
        return WorkspaceTable([])

    def get_resource(self, workspace: str, resource: str) -> AQTResource:
        resources = self.workspaces().workspace(workspace)
        if resources is None:
            raise ValueError(f"Workpace '{workspace}' is not accessible.")

        api_resource = None
        for resource_data in resources:
            if resource_data.get("id") == resource:
                api_resource = resource_data
                break
        else:
            raise ValueError(f"Resource '{resource}' does not exist in workspace '{workspace}'.")

        return AQTResource(self, workspace, api_resource)

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
