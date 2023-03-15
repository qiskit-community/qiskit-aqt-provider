# This code is part of Qiskit.
#
# (C) Copyright IBM 2019.
#
# This code is licensed under the Apache License, Version 2.0. You may
# obtain a copy of this license in the LICENSE.txt file in the root directory
# of this source tree or at http://www.apache.org/licenses/LICENSE-2.0.
#
# Any modifications or derivative works of this code must retain this
# copyright notice, and modified files need to carry a notice indicating
# that they have been altered from the originals.

from math import pi

import pytest
from qiskit import QuantumCircuit

from qiskit_aqt_provider.circuit_to_aqt import circuit_to_aqt_new


def test_empty_circuit() -> None:
    """Circuit need at least one measurement operation."""
    qc = QuantumCircuit(1)
    with pytest.raises(ValueError):
        circuit_to_aqt_new(qc, shots=1)


def test_just_measure_circuit() -> None:
    """Circuits with only measurement operations are valid."""
    shots = 100

    qc = QuantumCircuit(1)
    qc.measure_all()

    expected = {
        "job_type": "quantum_circuit",
        "label": "qiskit",
        "payload": {"quantum_circuit": [{"operation": "MEASURE"}], "repetitions": shots},
    }

    result = circuit_to_aqt_new(qc, shots=shots)

    assert result == expected


def test_valid_circuit() -> None:
    """A valid circuit with all supported basis gates."""
    qc = QuantumCircuit(2)
    qc.r(pi / 2, 0, 0)
    qc.rz(pi / 5, 1)
    qc.rxx(pi / 2, 0, 1)
    qc.measure_all()

    result = circuit_to_aqt_new(qc, shots=1)

    expected = {
        "job_type": "quantum_circuit",
        "label": "qiskit",
        "payload": {
            "repetitions": 1,
            "quantum_circuit": [
                {
                    "operation": "R",
                    "theta": 0.5,
                    "phi": 0.0,
                    "qubit": 0,
                },
                {
                    "operation": "RZ",
                    "phi": 0.2,
                    "qubit": 1,
                },
                {
                    "operation": "RXX",
                    "theta": 0.5,
                    "qubits": [0, 1],
                },
                {
                    "operation": "MEASURE",
                },
            ],
        },
    }

    assert result == expected


def test_invalid_gates_in_circuit() -> None:
    """Circuits must already be in the target basis when they are converted
    to the AQT wire format."""
    qc = QuantumCircuit(1)
    qc.h(0)  # not an AQT-resource basis gate
    qc.measure_all()

    with pytest.raises(ValueError):
        circuit_to_aqt_new(qc, shots=1)


def test_invalid_measurements() -> None:
    """Measurement operations can only be located at the end of the circuit."""

    qc_invalid = QuantumCircuit(2, 2)
    qc_invalid.r(pi / 2, 0.0, 0)
    qc_invalid.measure([0], [0])
    qc_invalid.r(pi / 2, 0.0, 1)
    qc_invalid.measure([1], [1])

    with pytest.raises(ValueError):
        circuit_to_aqt_new(qc_invalid, shots=1)

    # same circuit as above, but with the measurements at the end is valid
    qc = QuantumCircuit(2, 2)
    qc.r(pi / 2, 0.0, 0)
    qc.r(pi / 2, 0.0, 1)
    qc.measure([0], [0])
    qc.measure([1], [1])

    result = circuit_to_aqt_new(qc, shots=1)
    expected = {
        "job_type": "quantum_circuit",
        "label": "qiskit",
        "payload": {
            "repetitions": 1,
            "quantum_circuit": [
                {
                    "operation": "R",
                    "theta": 0.5,
                    "phi": 0.0,
                    "qubit": 0,
                },
                {
                    "operation": "R",
                    "theta": 0.5,
                    "phi": 0.0,
                    "qubit": 1,
                },
                {
                    "operation": "MEASURE",
                },
            ],
        },
    }

    assert result == expected
