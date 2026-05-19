from qiskit import QuantumCircuit
from qiskit.circuit.library import RGate, RXXGate, RZGate
from qiskit.circuit.measure import Measure
from qiskit.circuit.parameter import Parameter
from qiskit.providers import BackendV2, JobV1
from qiskit.transpiler import Target

from qiskit_aqt_provider.transpiler_plugin import TranspilerMixin


class DummyResource(BackendV2, TranspilerMixin):
    """A simple test resource for use in transpilation output tests."""

    def __init__(self) -> None:
        super().__init__(name="test_resource")
        target = Target(num_qubits=12)
        target.add_instruction(RZGate(Parameter("λ")))
        target.add_instruction(RGate(Parameter("θ"), Parameter("φ")))
        target.add_instruction(RXXGate(Parameter("θ")))
        target.add_instruction(Measure())
        self._target = target

    @property
    def id(self) -> str:  # noqa: D102
        return "test_resource"

    @property
    def target(self) -> Target:  # noqa: D102
        return self._target

    @property
    def max_circuits(self) -> int:  # noqa: D102
        return 50

    @classmethod
    def _default_options(cls) -> object:
        return {}

    def run(self, circuits: QuantumCircuit | list[QuantumCircuit]) -> JobV1:  # noqa: D102
        raise NotImplementedError("This is a dummy resource for testing and does not support running circuits.")
