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

import numpy as np
import numpy.testing as npt
from qiskit import QuantumCircuit
from qiskit_aer import AerSimulator
from scipy import optimize


def assert_circuits_equal(result: QuantumCircuit, expected: QuantumCircuit) -> None:
    """Assert result == expected, pretty-printing the circuits if they don't match."""
    msg = f"\nexpected:\n{expected}\nresult:\n{result}"
    assert result == expected, msg


def assert_circuits_equivalent(
    result: QuantumCircuit, expected: QuantumCircuit, *, atol=1e-7
) -> None:
    """Assert that the passed circuits are equivalent up to a global phase.

    The Qiskit-Aer unitary simulator is used to determine the unitary of both circuits
    and compare them after fitting the best global phase for the 'expected' circuit.

    The input circuits MUST NOT use the `save_state` directive, as this would interfere
    with the unitary retrieved from the simulator.
    """
    backend = AerSimulator(method="unitary")

    # Get unitary for 'result' circuit.
    result_circuit = result.copy()
    result_circuit.save_state()
    job = backend.run(result_circuit)
    u_result = job.result().get_unitary(0).data

    # Parametric unitary for 'expected' circuit
    def u_expected(global_phase: float) -> np.ndarray:
        expected_circuit = expected.copy()
        expected_circuit.global_phase = global_phase
        expected_circuit.save_state()

        return backend.run(expected_circuit).result().get_unitary(0).data

    # Find the best-fitting global phase for the 'expected' circuit
    def minimize_target(global_phase: float) -> float:
        u_diff = u_expected(global_phase) - u_result
        return (u_diff * u_diff.conj()).sum().real

    res = optimize.minimize_scalar(minimize_target)

    # Assert that the 'expected' circuit with the fitted global phase has the
    # same unitary as the 'result' circuit.
    msg = f"\nexpected:\n{expected}\nresult:\n{result}"
    npt.assert_allclose(u_expected(res.x), u_result, atol=atol, err_msg=msg)


def qft_circuit(num_qubits: int) -> QuantumCircuit:
    """N-qubits quantum Fourier transform.

    Source: Nielsen & Chuang, Quantum Computation and Quantum Information."""
    qc = QuantumCircuit(num_qubits)
    for qubit in range(num_qubits - 1, -1, -1):
        qc.h(qubit)
        for k in range(1, qubit + 1):
            qc.cp(np.pi / 2**k, qubit - k, qubit)

    for qubit in range(num_qubits // 2):
        qc.swap(qubit, (num_qubits - 1) - qubit)

    return qc
