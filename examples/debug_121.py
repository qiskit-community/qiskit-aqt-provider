from typing import Any, Union

import qiskit
from qiskit import QuantumCircuit
from qiskit.circuit.library import Measure, RXGate, RXXGate, RZGate
from qiskit.circuit.parameter import Parameter
from qiskit.providers import BackendV2, Options
from qiskit.transpiler import Target
from qiskit_aer import AerJob, AerProvider

from qiskit_aqt_provider import transpiler_plugin


class Backend(BackendV2):
    def __init__(self) -> None:
        super().__init__(name="dummy")

    @property
    def target(self) -> Target:
        theta = Parameter("theta")
        lam = Parameter("lambda")

        target = Target(num_qubits=10)
        target.add_instruction(RZGate(lam))
        target.add_instruction(RXGate(theta))
        target.add_instruction(RXXGate(theta))
        target.add_instruction(Measure())
        return target

    @property
    def max_circuits(self) -> int:
        return 100

    @classmethod
    def _default_options(cls) -> Options:
        return Options()

    def run(self, circuits: Union[QuantumCircuit, list[QuantumCircuit]], **options: Any) -> AerJob:
        sim = AerProvider().get_backend("aer_simulator")
        return sim.run(circuits, **options)


if __name__ == "__main__":
    qc = QuantumCircuit(2)
    qc.h(0)
    qc.cx(0, 1)
    qc.measure_all()

    backend = Backend()

    c1 = qiskit.transpile(qc, backend)
    print("C1 CX", c1.get_instructions("cx"))
    print("C1 RXX", c1.get_instructions("rxx"))

    pm = transpiler_plugin.bound_pass_manager(backend.target)
    c2 = pm.run(c1)
    print("C2 CX", c2.get_instructions("cx"))
    print("C2 RXX", c2.get_instructions("rxx"))
