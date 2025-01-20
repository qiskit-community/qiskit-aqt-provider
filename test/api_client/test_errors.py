# This code is part of Qiskit.
#
# (C) Copyright Alpine Quantum Technologies GmbH 2025.
#
# This code is licensed under the Apache License, Version 2.0. You may
# obtain a copy of this license in the LICENSE.txt file in the root directory
# of this source tree or at http://www.apache.org/licenses/LICENSE-2.0.
#
# Any modifications or derivative works of this code must retain this
# copyright notice, and modified files need to carry a notice indicating
# that they have been altered from the originals.


from contextlib import AbstractContextManager
from typing import Any

import httpx
import pytest

from qiskit_aqt_provider.api_client.errors import APIError, http_response_raise_for_status


def test_http_response_raise_for_status_no_error() -> None:
    """Test the wrapper around httpx.Response.raise_for_status when there is no error."""
    response = httpx.Response(status_code=httpx.codes.OK)
    # Set a dummy request (required to call raise_for_status).
    response.request = httpx.Request(method="GET", url="https://example.com")

    ret_response = http_response_raise_for_status(response)

    # The passed response is returned as-is.
    assert ret_response is response


@pytest.mark.parametrize(
    ("response", "expected"),
    [
        pytest.param(
            httpx.Response(status_code=httpx.codes.INTERNAL_SERVER_ERROR),
            pytest.raises(APIError),
            id="no-detail",
        ),
        pytest.param(
            httpx.Response(
                status_code=httpx.codes.INTERNAL_SERVER_ERROR, json={"detail": "error_message"}
            ),
            pytest.raises(APIError, match="error_message"),
            id="with-detail",
        ),
    ],
)
def test_http_response_raise_for_status_error(
    response: httpx.Response, expected: AbstractContextManager[pytest.ExceptionInfo[Any]]
) -> None:
    """Test the wrapper around httpx.Response.raise_for_status when the response contains an error.

    The wrapper re-packs the httpx.HTTPStatusError into a custom APIError, sets
    the latter's message to the error detail (if available), and propagates the
    original exception as cause for the APIError.
    """
    # Set dummy request (required to call raise_for_status).
    response.request = httpx.Request(method="GET", url="https://example.com")

    with expected as excinfo:
        http_response_raise_for_status(response)

    # Test cases all derive from a HTTP error status.
    # Check that the exception chain has the relevant information.
    status_error = excinfo.value.__cause__
    assert isinstance(status_error, httpx.HTTPStatusError)
    assert status_error.response.status_code == response.status_code
