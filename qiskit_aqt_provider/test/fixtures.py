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

import uuid
from typing import List, Tuple

import pytest
from qiskit.circuit import QuantumCircuit
from typing_extensions import override

from qiskit_aqt_provider import api_models
from qiskit_aqt_provider.aqt_job import AQTJob
from qiskit_aqt_provider.aqt_provider import AQTProvider
from qiskit_aqt_provider.aqt_resource import OfflineSimulatorResource


class MockSimulator(OfflineSimulatorResource):
    """Offline simulator that keeps track of the submitted circuits."""

    def __init__(self, *, noisy: bool) -> None:
        super().__init__(
            AQTProvider(""),
            resource_id=api_models.ResourceId(
                workspace_id="default",
                resource_id="mock_simulator",
                resource_name="mock_simulator",
                resource_type="offline_simulator",
            ),
            with_noise_model=noisy,
        )

        self.submit_call_args: List[Tuple[List[QuantumCircuit], int]] = []

    @override
    def submit(self, job: AQTJob) -> uuid.UUID:
        """Submit the circuits for execution on the backend.

        Record the passed arguments in `submit_call_args`.

        Args:
            job: AQTJob to submit to the mock simulator.
        """
        self.submit_call_args.append((job.circuits, job.options.shots))
        return super().submit(job)

    @property
    def submitted_circuits(self) -> List[List[QuantumCircuit]]:
        """Circuit batches passed to the resource for execution, in submission order."""
        return [circuit for circuit, _ in self.submit_call_args]


@pytest.fixture(name="offline_simulator_no_noise")
def fixture_offline_simulator_no_noise() -> MockSimulator:
    """Noiseless offline simulator resource."""
    return MockSimulator(noisy=False)
