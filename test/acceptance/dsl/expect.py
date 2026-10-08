# This code is part of Qiskit.
#
# (C) Copyright Alpine Quantum Technologies GmbH 2023
#
# This code is licensed under the Apache License, Version 2.0. You may
# obtain a copy of this license in the LICENSE.txt file in the root directory
# of this source tree or at [http://www.apache.org/licenses/LICENSE-2.0](http://www.apache.org/licenses/LICENSE-2.0).
#
# Any modifications or derivative works of this code must retain this
# copyright notice, and modified files need to carry a notice indicating
# that they have been altered from the originals.

from collections.abc import Iterator
from contextlib import contextmanager

import pytest
from qiskit.providers.exceptions import QiskitBackendNotFoundError

from qiskit_aqt_provider.api_client.errors import APIError


@contextmanager
def backend_not_found(workspace_id: str, resource_id: str) -> Iterator[None]:
    """Context manager for expecting a QiskitBackendNotFoundError to be raised."""
    with pytest.raises(
        QiskitBackendNotFoundError, match=f"Backend with ID '{resource_id}' not found in workspace '{workspace_id}'."
    ):
        yield


@contextmanager
def job_submission_fails_with_message(expected_message: str) -> Iterator[None]:
    """Context manager for expecting a job submission to fail with a specific message."""
    with pytest.raises(APIError, match=expected_message):
        yield
