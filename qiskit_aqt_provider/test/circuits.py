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

"""Test helpers for quantum circuits."""

import math

import qiskit.circuit.random
from qiskit import QuantumCircuit
from qiskit.quantum_info.operators import Operator


def assert_circuits_equal(result: QuantumCircuit, expected: QuantumCircuit) -> None:
    """Assert result == expected, pretty-printing the circuits if they don't match."""
    msg = f"\nexpected:\n{expected}\nresult:\n{result}"
    assert result == expected, msg  # noqa: S101


def assert_circuits_equal_ignore_global_phase(
    result: QuantumCircuit, expected: QuantumCircuit
) -> None:
    """Assert result == expected, ignoring the value of the global phase."""
    result_copy = result.copy()
    result_copy.global_phase = 0.0
    expected_copy = expected.copy()
    expected_copy.global_phase = 0.0

    assert_circuits_equal(result_copy, expected_copy)


def assert_circuits_equivalent(result: QuantumCircuit, expected: QuantumCircuit) -> None:
    """Assert that the passed circuits are equivalent up to a global phase."""
    msg = f"\nexpected:\n{expected}\nresult:\n{result}"
    assert Operator.from_circuit(expected).equiv(Operator.from_circuit(result)), msg  # noqa: S101


def empty_circuit(num_qubits: int, with_final_measurement: bool = True) -> QuantumCircuit:
    """An empty circuit, with the given number of qubits."""
    qc = QuantumCircuit(num_qubits)

    if with_final_measurement:
        qc.measure_all()

    return qc


def random_circuit(
    num_qubits: int, *, seed: int = 1234, with_final_measurement: bool = True
) -> QuantumCircuit:
    """A random circuit, with depth equal to the number of qubits."""
    qc = qiskit.circuit.random.random_circuit(
        num_qubits,
        num_qubits,
        seed=seed,
    )

    if with_final_measurement:
        qc.measure_all()

    return qc


def qft_circuit(num_qubits: int) -> QuantumCircuit:
    """N-qubits quantum Fourier transform.

    Source: Nielsen & Chuang, Quantum Computation and Quantum Information.
    """
    qc = QuantumCircuit(num_qubits)
    for qubit in range(num_qubits - 1, -1, -1):
        qc.h(qubit)
        for k in range(1, qubit + 1):
            qc.cp(math.pi / 2**k, qubit - k, qubit)

    for qubit in range(num_qubits // 2):
        qc.swap(qubit, (num_qubits - 1) - qubit)

    return qc
