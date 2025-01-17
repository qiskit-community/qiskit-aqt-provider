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


from contextlib import AbstractContextManager, nullcontext
from typing import Any, Optional

import httpx
import pytest

from qiskit_aqt_provider.api_client.errors import APIError, http_response_raise_for_status


@pytest.mark.parametrize(
    ("response", "expected"),
    [
        pytest.param(httpx.Response(status_code=httpx.codes.OK), nullcontext(), id="ok"),
        pytest.param(
            httpx.Response(status_code=httpx.codes.INTERNAL_SERVER_ERROR),
            pytest.raises(APIError),
            id="error-no-detail",
        ),
        pytest.param(
            httpx.Response(
                status_code=httpx.codes.INTERNAL_SERVER_ERROR, json={"detail": "error_message"}
            ),
            pytest.raises(APIError, match="error_message"),
            id="error-with-detail",
        ),
    ],
)
def test_http_response_raise_for_status(
    response: httpx.Response, expected: AbstractContextManager[Optional[pytest.ExceptionInfo[Any]]]
) -> None:
    """Test the wrapper around httpx.Response.raise_for_status.

    The wrapper re-packs the httpx.HTTPStatusError into a custom APIError, sets
    the latter's message to the error detail (if available), and propagates the
    original exception as cause for the APIError.
    """
    # Set dummy request (required because HTTPStatusError propagates the request).
    response.request = httpx.Request(method="GET", url="https://example.com")

    with expected as excinfo:
        http_response_raise_for_status(response)

    # Error test cases all derive from a HTTP error status.
    # Check that the exception chain has the relevant information.
    if excinfo is not None:
        status_error = excinfo.value.__cause__
        assert isinstance(status_error, httpx.HTTPStatusError)
        assert status_error.response.status_code == response.status_code
