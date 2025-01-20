# This code is part of Qiskit.
#
# (C) Copyright Alpine Quantum Technologies GmbH 2025
#
# This code is licensed under the Apache License, Version 2.0. You may
# obtain a copy of this license in the LICENSE.txt file in the root directory
# of this source tree or at http://www.apache.org/licenses/LICENSE-2.0.
#
# Any modifications or derivative works of this code must retain this
# copyright notice, and modified files need to carry a notice indicating
# that they have been altered from the originals.

import json
from typing import Any

import httpx


class APIError(Exception):
    """An API request failed.

    Instances of this class are raised when errors occur while communicating
    with the target resource API (for both remote and direct-access resources).

    If the underlying API request failed with an error status, the exception chain
    contains the original `httpx.HTTPStatusError <https://www.python-httpx.org/exceptions/#:~:text=httpx.HTTPStatusError>`_
    """

    def __init__(self, detail: Any) -> None:
        """Initialize the exception instance.

        Args:
            detail: error description payload. The string representation is used as error message.
        """
        super().__init__(str(detail) if detail is not None else "Unspecified error")

        # Keep the original object, in case it wasn't a string.
        self.detail = detail


def http_response_raise_for_status(response: httpx.Response) -> httpx.Response:
    """Check the HTTP status of a response payload.

    Returns:
        The passed HTTP response, unchanged.

    Raises:
        APIError: the API response contains an error status.
    """
    try:
        return response.raise_for_status()
    except httpx.HTTPStatusError as status_error:
        try:
            detail = response.json().get("detail")
        except (json.JSONDecodeError, UnicodeDecodeError, AttributeError):
            detail = None

        raise APIError(detail) from status_error
