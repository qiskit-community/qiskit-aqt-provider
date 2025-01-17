# (C) Copyright Alpine Quantum Technologies GmbH 2024
#
# This code is licensed under the Apache License, Version 2.0. You may
# obtain a copy of this license in the LICENSE.txt file in the root directory
# of this source tree or at http://www.apache.org/licenses/LICENSE-2.0.
#
# Any modifications or derivative works of this code must retain this
# copyright notice, and modified files need to carry a notice indicating
# that they have been altered from the originals.

import os
from typing import Final, Optional

import httpx

from qiskit_aqt_provider.api_client.errors import http_response_raise_for_status

from . import models
from .versions import make_user_agent

DEFAULT_PORTAL_URL: Final = httpx.URL("https://arnica.aqt.eu")
"""Default URL for the remote portal."""


class PortalClient:
    """Client for the AQT portal API."""

    USER_AGENT_NAME: Final = "aqt-portal-client"

    def __init__(
        self, *, token: str, user_agent_extra: Optional[str] = None, timeout: Optional[float] = 10.0
    ) -> None:
        """Initialize a new client for the AQT remote computing portal API.

        By default, the client connects to the portal at :py:data:`DEFAULT_PORTAL_URL`.
        This can be overridden using the ``AQT_PORTAL_URL`` environment variable.

        Args:
            token: authentication token.
            user_agent_extra: data appended to the default user-agent string.
            timeout: HTTP timeout, in seconds.
        """
        self.portal_url = httpx.URL(os.environ.get("AQT_PORTAL_URL", DEFAULT_PORTAL_URL))

        user_agent = make_user_agent(self.USER_AGENT_NAME, extra=user_agent_extra)
        headers = {"User-Agent": user_agent}

        if token:
            headers["Authorization"] = f"Bearer {token}"

        self._http_client = httpx.Client(
            base_url=self.portal_url.join("/api/v1"),
            headers=headers,
            timeout=timeout,
            follow_redirects=True,
        )

    def workspaces(self) -> models.Workspaces:
        """List the workspaces visible to the used token.

        Raises:
            httpx.NetworkError: connection to the remote portal failed.
            APIError: something went wrong with the request to the remote portal.
        """
        with self._http_client as client:
            response = http_response_raise_for_status(client.get("/workspaces"))

        return models.Workspaces.model_validate(response.json())
