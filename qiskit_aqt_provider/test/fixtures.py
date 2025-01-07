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

import json
import re
import typing
import uuid

import httpx
import pytest
from pytest_httpx import HTTPXMock
from qiskit.circuit import QuantumCircuit
from qiskit_aer import AerSimulator
from typing_extensions import override

from qiskit_aqt_provider import api_client
from qiskit_aqt_provider.api_client import models as api_models
from qiskit_aqt_provider.api_client import models_direct as api_models_direct
from qiskit_aqt_provider.aqt_job import AQTJob
from qiskit_aqt_provider.aqt_provider import AQTProvider
from qiskit_aqt_provider.aqt_resource import (
    AnyAQTResource,
    AQTDirectAccessResource,
    OfflineSimulatorResource,
    qubit_states_from_int,
)
from qiskit_aqt_provider.circuit_to_aqt import aqt_to_qiskit_circuit
from qiskit_aqt_provider.test.resources import DummyDirectAccessResource


class MockSimulator(OfflineSimulatorResource):
    """Offline simulator that keeps track of the submitted circuits."""

    def __init__(self, *, noisy: bool) -> None:
        """Initialize the mocked simulator backend."""
        super().__init__(
            AQTProvider(""),
            resource_id=api_client.Resource(
                workspace_id="default",
                resource_id="mock_simulator",
                resource_name="mock_simulator",
                resource_type="offline_simulator",
            ),
            with_noise_model=noisy,
        )

        self.submit_call_args: list[tuple[list[QuantumCircuit], int]] = []

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
    def submitted_circuits(self) -> list[list[QuantumCircuit]]:
        """Circuit batches passed to the resource for execution, in submission order."""
        return [circuit for circuit, _ in self.submit_call_args]


@pytest.fixture(name="offline_simulator_no_noise")
def fixture_offline_simulator_no_noise() -> MockSimulator:
    """Noiseless offline simulator resource, as cloud backend."""
    return MockSimulator(noisy=False)


@pytest.fixture(name="offline_simulator_no_noise_direct_access")
def fixture_offline_simulator_no_noise_direct_access(
    httpx_mock: HTTPXMock,
) -> AQTDirectAccessResource:
    """Noiseless offline simulator resource, as direct-access backend."""
    simulator = AerSimulator(method="statevector")

    inflight_circuits: dict[uuid.UUID, api_models.QuantumCircuit] = {}

    def handle_submit(request: httpx.Request) -> httpx.Response:
        data = api_models.QuantumCircuit.model_validate_json(request.content.decode("utf-8"))

        job_id = uuid.uuid4()
        inflight_circuits[job_id] = data.model_copy(deep=True)

        return httpx.Response(
            status_code=httpx.codes.OK,
            text=f'"{job_id}"',
        )

    def handle_result(request: httpx.Request) -> httpx.Response:
        _, job_id_str = request.url.path.rsplit("/", maxsplit=1)
        job_id = uuid.UUID(job_id_str)

        data = inflight_circuits[job_id]
        qiskit_circuit = aqt_to_qiskit_circuit(data.quantum_circuit, data.number_of_qubits)
        result = simulator.run(qiskit_circuit, shots=data.repetitions).result()

        samples: list[list[int]] = []
        for hex_state, occurrences in result.data()["counts"].items():
            samples.extend(
                [
                    qubit_states_from_int(int(hex_state, 16), qiskit_circuit.num_qubits)
                    for _ in range(occurrences)
                ]
            )

        return httpx.Response(
            status_code=httpx.codes.OK,
            json=json.loads(
                api_models_direct.JobResult.create_finished(
                    job_id=job_id,
                    result=samples,
                ).model_dump_json()
            ),
        )

    httpx_mock.add_callback(handle_submit, method="PUT", url=re.compile(".+/circuit/?$"))
    httpx_mock.add_callback(
        handle_result, method="GET", url=re.compile(".+/circuit/result/[0-9a-f-]+$")
    )

    return DummyDirectAccessResource("token")


@pytest.fixture(
    name="any_offline_simulator_no_noise",
    params=["offline_simulator_no_noise", "offline_simulator_no_noise_direct_access"],
)
def fixture_any_offline_simulator_no_noise(request: pytest.FixtureRequest) -> AnyAQTResource:
    """Noiseless, offline simulator backend.

    The fixture is parametrized to successively run the dependent tests
    with a regular cloud-bound backend, and a direct-access one.
    """
    # cast: all fixture parameters have types compatible with this function's return type.
    return typing.cast(AnyAQTResource, request.getfixturevalue(request.param))
