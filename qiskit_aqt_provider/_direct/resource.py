from collections.abc import Sequence
from dataclasses import dataclass
from functools import partial

import pydantic as pdt
from aqt_connector.models.circuits import QuantumCircuit as AQTQuantumCircuit
from qiskit.circuit import QuantumCircuit
from qiskit.circuit.library import RGate, RXXGate, RZGate
from qiskit.circuit.measure import Measure
from qiskit.circuit.parameter import Parameter
from qiskit.providers import BackendV2, JobV1
from qiskit.transpiler import Target

from qiskit_aqt_provider._direct.api_client import DirectAccessAPIClient
from qiskit_aqt_provider._direct.composite_job import (
    CompositeDirectAccessJob,
    CompositeDirectAccessJobMetadata,
)
from qiskit_aqt_provider._direct.job import DirectAccessJob, DirectAccessJobMetadata
from qiskit_aqt_provider.circuit_to_aqt import qiskit_to_aqt_circuit
from qiskit_aqt_provider.transpiler_plugin import TranspilerMixin


@dataclass
class DirectAccessResourceConfig:
    name: str
    number_of_ions: int
    client: DirectAccessAPIClient


class DirectAccessOptions(pdt.BaseModel):
    """Options for a direct access resource."""

    shots: pdt.PositiveInt = pdt.Field(default=100)


class DirectAccessResource(BackendV2, TranspilerMixin):
    """A resource with direct access."""

    MAX_SHOTS = 2000

    def __init__(self, config: DirectAccessResourceConfig) -> None:
        """Initializes a direct access resource with the given configuration."""
        self._api_client = config.client
        self._resource_id = config.name
        super().__init__(name=config.name)
        self._update_target(config.number_of_ions)

    @property
    def id(self) -> str:
        """The resource's identifier."""
        return self._resource_id

    @property
    def target(self) -> Target:
        """The resource's target."""
        return self._target

    @property
    def max_circuits(self) -> int:
        """Maximum number of circuits per batch."""
        return 50

    @classmethod
    def _default_options(cls) -> DirectAccessOptions:
        """Get the default options.

        Returns:
            DirectAccessOptions: The default options for this resource.
        """
        return DirectAccessOptions()

    def run(self, circuit: QuantumCircuit | Sequence[QuantumCircuit], *, shots: int | None = None) -> JobV1:
        shots = shots if shots is not None else self._options.shots
        if shots < 1 or shots > self.MAX_SHOTS:
            raise ValueError(f"Shots must be in the range [1, {self.MAX_SHOTS}].")

        if isinstance(circuit, QuantumCircuit):
            return self._prepare_single_circuit_job(circuit, shots)

        return self._prepare_multi_circuit_job(circuit, shots)

    def _update_target(self, num_qubits: int) -> None:
        """Updates the target of this resource based on the given number of qubits."""
        theta = Parameter("θ")
        phi = Parameter("φ")
        lam = Parameter("λ")

        target = Target(num_qubits=num_qubits)
        target.add_instruction(RZGate(lam))
        target.add_instruction(RGate(theta, phi))
        target.add_instruction(RXXGate(theta))
        target.add_instruction(Measure())

        self._target = target

    def _prepare_single_circuit_job(self, circuit: QuantumCircuit, shots: int) -> DirectAccessJob:
        """Creates a DirectAccessJob for a single circuit."""
        payload = AQTQuantumCircuit(
            repetitions=shots,
            quantum_circuit=qiskit_to_aqt_circuit(circuit),
            number_of_qubits=circuit.num_qubits,
        )
        metadata = DirectAccessJobMetadata(backend_name=self._resource_id, shots=shots, circuit=circuit)
        return self._submit_one(payload, metadata)

    def _prepare_multi_circuit_job(self, circuits: Sequence[QuantumCircuit], shots: int) -> CompositeDirectAccessJob:
        """Creates a CompositeDirectAccessJob for multiple circuits."""
        payloads = [
            AQTQuantumCircuit(
                repetitions=shots,
                quantum_circuit=qiskit_to_aqt_circuit(c),
                number_of_qubits=c.num_qubits,
            )
            for c in circuits
        ]
        circuit_metadata = [
            DirectAccessJobMetadata(backend_name=self._resource_id, shots=shots, circuit=c) for c in circuits
        ]
        job_submitters = [partial(self._submit_one, p, m) for p, m in zip(payloads, circuit_metadata)]

        composite_metadata = CompositeDirectAccessJobMetadata(backend_name=self._resource_id)
        return CompositeDirectAccessJob(composite_metadata, job_submitters)

    def _submit_one(self, payload: AQTQuantumCircuit, metadata: DirectAccessJobMetadata) -> DirectAccessJob:
        """Submits a single circuit to the resource and returns the corresponding job."""
        job_id = self._api_client.submit_circuit(payload)
        return DirectAccessJob(self._api_client, job_id, metadata)
