from __future__ import annotations

from collections.abc import Sequence
from typing import Any

from qiskit import QuantumCircuit
from qiskit.providers import BackendV2, JobV1, Options
from qiskit.transpiler import Target

from qiskit_aqt_provider.primitives._transpiling_backend import TranspilingBackend


class _RecordingResource(BackendV2):
    def __init__(self) -> None:
        self.run_calls: list[dict[str, Any]] = []
        self.returned_job = object()
        super().__init__(name="recording_resource")
        self._target = Target(num_qubits=1)

    @property
    def id(self) -> str:
        return "recording_resource"

    @property
    def target(self) -> Target:
        return self._target

    @property
    def max_circuits(self) -> int:
        return 50

    @classmethod
    def _default_options(cls) -> Options:
        return Options()

    def run(self, circuit: QuantumCircuit | Sequence[QuantumCircuit], **kwargs: Any) -> JobV1:
        self.run_calls.append({"circuit": circuit, "kwargs": kwargs})
        return self.returned_job


def test_run_transpiles_then_forwards_to_wrapped_backend() -> None:
    """It should transpile the input circuit and then forward it to the wrapped backend's run method."""
    resource = _RecordingResource()
    input_circuit = QuantumCircuit(1)
    input_circuit.measure_all()
    transpiled_circuit = QuantumCircuit(1)

    seen: dict[str, Any] = {}

    def transpile_double(
        circuit: QuantumCircuit | Sequence[QuantumCircuit], backend: BackendV2
    ) -> QuantumCircuit | Sequence[QuantumCircuit]:
        seen["circuit"] = circuit
        seen["backend"] = backend
        return transpiled_circuit

    backend = TranspilingBackend(resource, transpile_fn=transpile_double)

    result = backend.run(input_circuit, shots=123)

    assert seen == {"circuit": input_circuit, "backend": resource}
    assert resource.run_calls == [{"circuit": transpiled_circuit, "kwargs": {"shots": 123}}]
    assert result is resource.returned_job
