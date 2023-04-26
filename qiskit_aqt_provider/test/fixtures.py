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

from qiskit_aqt_provider.aqt_provider import AQTProvider
from qiskit_aqt_provider.aqt_resource import ApiResource, OfflineSimulatorResource
from qiskit_aqt_provider.circuit_to_aqt import _qiskit_to_aqt_circuit


class MockSimulator(OfflineSimulatorResource):
    """Offline simulator that keeps track of the submitted circuits."""

    def __init__(self) -> None:
        super().__init__(
            AQTProvider(""),
            "default",
            ApiResource(name="mock_simulator", id="mock_simulator", type="offline_simulator"),
        )

        self.submit_call_args: List[Tuple[List[QuantumCircuit], int]] = []

    def submit(self, circuits: List[QuantumCircuit], shots: int) -> uuid.UUID:
        """Submit the circuits for execution on the backend.

        Record the passed arguments in `submit_call_args`.

        Try to convert the circuits to the AQT JSON wire format.

        Args:
            circuits: the circuits to execute on the simulator
            shots: number of repetitions.

        Raises:
            ValueError: at least one circuit cannot be converted to the AQT JSON wire format.
        """
        for circuit in circuits:
            try:
                _ = _qiskit_to_aqt_circuit(circuit)
            except Exception as e:  # noqa: BLE001
                raise ValueError(
                    f"Circuit cannot be converted to AQT JSON format:\n{circuit}"
                ) from e

        self.submit_call_args.append((circuits, shots))
        return super().submit(circuits, shots)

    @property
    def submitted_circuits(self) -> List[List[QuantumCircuit]]:
        """Circuit batches passed to the resource for execution, in submission order."""
        return [circuit for circuit, _ in self.submit_call_args]


@pytest.fixture(name="offline_simulator_no_noise")
def fixture_offline_simulator_no_noise() -> MockSimulator:
    """Noiseless offline simulator resource."""
    return MockSimulator()
