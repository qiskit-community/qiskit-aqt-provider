
from qiskit import QuantumCircuit
from qiskit.quantum_info import Operator


def assert_circuits_equivalent(circ1: QuantumCircuit, circ2: QuantumCircuit) -> None:
    """Helper function to assert that two quantum circuits are equivalent.

    This is done by comparing their unitary operators. Alternatively we could decompose both circuits
    and compare the resulting sequences of gates, but comparing unitaries is more straightforward for
    this test.
    """
    assert Operator(circ1).equiv(Operator(circ2))
