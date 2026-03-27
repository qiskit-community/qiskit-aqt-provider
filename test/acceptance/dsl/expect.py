from collections.abc import Iterator
from contextlib import contextmanager

import pytest
from qiskit.providers.exceptions import QiskitBackendNotFoundError


@contextmanager
def backend_not_found(workspace_id: str, resource_id: str) -> Iterator[None]:
    """Context manager for expecting a QiskitBackendNotFoundError to be raised."""
    with pytest.raises(
        QiskitBackendNotFoundError, match=f"Backend with ID '{resource_id}' not found in workspace '{workspace_id}'."
    ):
        yield
