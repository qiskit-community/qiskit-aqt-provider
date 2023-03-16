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

from math import pi
from typing import Final

import pytest
from qiskit import QuantumCircuit, QuantumRegister, transpile

from qiskit_aqt_provider.aqt_resource import AQTResource
from qiskit_aqt_provider.test.circuits import (
    assert_circuits_equal,
    assert_circuits_equivalent,
    qft_circuit,
)
from qiskit_aqt_provider.transpiler_plugin import wrap_rxx_angle


@pytest.mark.parametrize(
    "angle,expected_angle",
    [
        (pi / 3, pi / 3),
        (7 * pi / 5, -3 * pi / 5),
        (25 * pi, -pi),
        (22 * pi / 3, -2 * pi / 3),
    ],
)
def test_rx_wrap_angle(
    angle: float, expected_angle: float, offline_simulator_no_noise: AQTResource
) -> None:
    """Check that transpiled rotation gate angles are wrapped to [-π,π]."""
    qc = QuantumCircuit(1)
    qc.rx(angle, 0)

    expected = QuantumCircuit(1)
    expected.r(expected_angle, 0, 0)

    result = transpile(qc, offline_simulator_no_noise, optimization_level=3)
    assert isinstance(result, QuantumCircuit)

    assert_circuits_equal(result, expected)


def test_rx_r_rewrite_simple(offline_simulator_no_noise: AQTResource) -> None:
    """Check that Rx gates are rewritten as R gates."""
    qc = QuantumCircuit(1)
    qc.rx(pi / 2, 0)

    expected = QuantumCircuit(1)
    expected.r(pi / 2, 0, 0)

    result = transpile(qc, offline_simulator_no_noise, optimization_level=3)
    assert isinstance(result, QuantumCircuit)  # only got one circuit back

    assert_circuits_equal(result, expected)


def test_decompose_1q_rotations_simple(offline_simulator_no_noise: AQTResource) -> None:
    """Check that runs of single-qubit rotations are optimized as a ZXZ."""
    qc = QuantumCircuit(1)
    qc.rx(pi / 2, 0)
    qc.ry(pi / 2, 0)

    expected = QuantumCircuit(1)
    expected.rz(-pi / 2, 0)
    expected.r(pi / 2, 0, 0)

    result = transpile(qc, offline_simulator_no_noise, optimization_level=3)
    assert isinstance(result, QuantumCircuit)  # only got one circuit back

    assert_circuits_equal(result, expected)


RXX_ANGLES: Final = [
    pi / 4,
    pi / 2,
    -pi / 2,
    3 * pi / 4,
    -3 * pi / 4,
    15 * pi / 8,
    -15 * pi / 8,
    33 * pi / 16,
    -33 * pi / 16,
]


@pytest.mark.parametrize("angle", RXX_ANGLES)
def test_rxx_wrap_angle(angle: float) -> None:
    """Check that the circuit returned by `wrap_rxx_angle`
    is equivalent to an Rxx operation with the passed angle."""

    qr = QuantumRegister(2)
    q0, q1 = qr._bits
    qc = wrap_rxx_angle(angle, q0, q1)

    # one rxx in, one rxx out!
    assert set(qc.count_ops()) <= {"rxx", "rz", "rx", "ry", "r"}
    assert qc.count_ops()["rxx"] == 1

    for operation in qc.data:
        instruction = operation[0]
        if instruction.name == "rxx":
            (theta,) = instruction.params
            assert abs(float(theta)) <= pi / 2
            break
    else:  # pragma: no cover
        assert False, "There must be at least one RXX operation in the circuit."

    expected = QuantumCircuit(2)
    expected.rxx(angle, 0, 1)

    assert_circuits_equivalent(qc, expected)


@pytest.mark.parametrize("angle", RXX_ANGLES)
def test_rxx_wrap_angle_transpile(angle: float, offline_simulator_no_noise: AQTResource) -> None:
    """Check that Rxx angles are wrapped by the transpiler."""
    qc = QuantumCircuit(2)
    qc.rxx(angle, 0, 1)
    trans_qc = transpile(qc, offline_simulator_no_noise, optimization_level=3)

    assert isinstance(trans_qc, QuantumCircuit)

    assert set(trans_qc.count_ops()) <= set(offline_simulator_no_noise.configuration().basis_gates)
    assert trans_qc.count_ops()["rxx"] == 1

    # check that all Rxx have angles in [-π/2, π/2]
    for operation in trans_qc.data:
        instruction = operation[0]
        if instruction.name == "rxx":
            (theta,) = instruction.params
            assert abs(float(theta)) <= pi / 2

    # check that the transpiled circuit is equivalent to the original one
    assert_circuits_equivalent(trans_qc, qc)


@pytest.mark.parametrize("qubits", [1, 5, 10])
@pytest.mark.parametrize("optimization_level", [0, 1, 2, 3])
def test_qft_circuit_transpilation(
    qubits: int, optimization_level: int, offline_simulator_no_noise: AQTResource
) -> None:
    """Transpile a N-qubit QFT circuit for an AQT backend. Check that the angles are properly
    wrapped."""
    qc = qft_circuit(qubits)
    trans_qc = transpile(qc, offline_simulator_no_noise, optimization_level=optimization_level)
    assert isinstance(trans_qc, QuantumCircuit)

    assert set(trans_qc.count_ops()) <= set(offline_simulator_no_noise.configuration().basis_gates)

    for operation in trans_qc.data:
        instruction = operation[0]
        if instruction.name == "rxx":
            (theta,) = instruction.params
            assert abs(float(theta)) <= pi / 2

        if instruction.name == "r":
            (theta, _) = instruction.params
            assert abs(theta) <= pi

    if optimization_level < 3 and qubits < 6:
        assert_circuits_equivalent(qc, trans_qc)
