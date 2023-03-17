# This code is part of Qiskit.
#
# (C) Alpine Quantum Technologies GmbH 2023
#
# This code is licensed under the Apache License, Version 2.0. You may
# obtain a copy of this license in the LICENSE.txt file in the root directory
# of this source tree or at http://www.apache.org/licenses/LICENSE-2.0.
#
# Any modifications or derivative works of this code must retain this
# copyright notice, and modified files need to carry a notice indicating
# that they have been altered from the originals.

"""Pytest fixtures for the AQT Qiskit provider.

This module is exposed as pytest plugin for this project.
"""

import abc
import uuid
from typing import Any, Dict, Final, Iterator, Set
from unittest.mock import patch

import pytest
from qiskit import QuantumCircuit

from qiskit_aqt_provider.aqt_provider import AQTProvider
from qiskit_aqt_provider.aqt_resource import (
    ApiResource,
    AQTResource,
    OfflineSimulatorResource,
)
from qiskit_aqt_provider.circuit_to_aqt import circuit_to_aqt_new


@pytest.fixture(name="offline_simulator_no_noise")
def fixture_offline_simulator_no_noise() -> Iterator[AQTResource]:
    """Noiseless offline simulator resource."""

    provider = AQTProvider("")
    resource = provider.get_resource("default", "offline_simulator_no_noise")
    with patch.object(OfflineSimulatorResource, "submit", wraps=resource.submit) as mock:
        yield resource

        # try to convert all circuits that were passed to the simulator
        # to the AQT API JSON format.
        for call_args in mock.call_args_list:
            # this could fail if submit() is (partially or fully) called with kwargs
            circuit, shots = call_args.args

            try:
                _ = circuit_to_aqt_new(circuit, shots=shots)
            # pylint: disable-next=broad-except
            except Exception:  # pragma: no cover
                pytest.fail(f"Circuit cannot be converted to the AQT JSON format:\n{circuit}")


@pytest.fixture(name="error_resource")
def fixture_error_resource() -> Iterator[AQTResource]:
    """An AQT resource that always returns well-formed error payloads.

    The error message returned by the resource is stored in the
    `error_str` attribute.
    """
    yield ErrorResource()


@pytest.fixture(name="non_compliant_resource")
def fixture_non_compliant_resource() -> Iterator[AQTResource]:
    """An AQT resource that always returns ill-formed payloads."""
    yield NonCompliantResource()


class AbstractDummyResource(AQTResource, abc.ABC):
    """Abstract dummy AQT resource."""

    def __init__(self) -> None:
        self.jobs: Set[str] = set()
        super().__init__(
            AQTProvider(""), "dummy", ApiResource(name="dummy", id="dummy", type="simulator")
        )

    def submit(self, circuit: QuantumCircuit, shots: int) -> str:
        job_id = str(uuid.uuid4())
        self.jobs.add(job_id)
        return job_id

    @abc.abstractmethod
    def result(self, job_id: str) -> Dict[str, Any]:
        ...  # pragma: no cover


class ErrorResource(AbstractDummyResource):
    """An AQT resource that always returns a well-formed error.

    The returned error string is unique between different instances.
    """

    def __init__(self) -> None:
        self.error_str: Final = str(uuid.uuid4())
        super().__init__()

    def result(self, job_id: str) -> Dict[str, Any]:
        self.jobs.remove(job_id)
        return {"response": {"status": "error", "message": self.error_str}}


class NonCompliantResource(AbstractDummyResource):
    """An AQT resource that always returns invalid payloads."""

    def result(self, job_id: str) -> Dict[str, Any]:
        self.jobs.remove(job_id)
        return {"invalid": "invalid"}
