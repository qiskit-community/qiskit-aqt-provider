import re
from math import copysign, pi

import pytest
from qiskit import QuantumCircuit
from qiskit.converters import circuit_to_dag, dag_to_circuit
from qiskit.transpiler import PassManager

from qiskit_aqt_provider.transpiler_plugin import WrapRxxAngles
from test.helpers import assert_circuits_equivalent


def run_pass(qc: QuantumCircuit) -> QuantumCircuit:
    """Helper function to run the WrapRxxAngles pass on a given quantum circuit."""
    pm = PassManager([WrapRxxAngles()])
    return pm.run(qc)


@pytest.mark.parametrize(
    ("theta"),
    [0, pi / 2, pi / 4],
)
def test_it_does_not_substitute_rxx_gates_with_angle_in_range(theta: float) -> None:
    """The pass should not modify RXX gates with angles in the range [0, π/2]."""
    qc = QuantumCircuit(2)
    qc.rxx(theta, 0, 1)

    dag = circuit_to_dag(qc)
    new_qc = dag_to_circuit(WrapRxxAngles().run(dag))

    assert len(new_qc.data) == 1
    assert new_qc.data[0].operation.name == "rxx"


def test_it_substitutes_rxx_gates_when_wrapping() -> None:
    """The pass should substitute the name of gates whose angles it wraps."""
    qc = QuantumCircuit(2)
    qc.rxx(2 * pi, 0, 1)

    dag = circuit_to_dag(qc)
    new_qc = dag_to_circuit(WrapRxxAngles().run(dag))

    assert len(new_qc.data) == 1
    assert re.match(r"Rxx-wrapped\(.+\)", new_qc.data[0].operation.name)


@pytest.mark.parametrize("theta", [0, pi / 6, pi / 2])
def test_it_does_not_change_rxx_gates_with_angles_in_range(theta: float) -> None:
    """It should not modify RXX gates with angles already in range [0, π/2]."""
    qc = QuantumCircuit(2)
    qc.rxx(theta, 0, 1)

    out = run_pass(qc)

    assert_circuits_equivalent(out, qc)


@pytest.mark.parametrize("theta", [-pi / 6, -pi / 2, -0.000001])
def test_it_wraps_small_negative_angles(theta: float) -> None:
    """It should wrap negative angles [-π/2, 0) by adding RZ gates and taking the absolute value of the angle."""
    qc = QuantumCircuit(2)
    qc.rxx(theta, 0, 1)
    expected = QuantumCircuit(2)
    expected.rz(pi, 0)
    expected.rxx(abs(theta), 0, 1)
    expected.rz(pi, 0)

    out = run_pass(qc)

    assert_circuits_equivalent(out, expected)


@pytest.mark.parametrize("theta", [pi, -pi, pi * 3 / 4, -pi * 3 / 4, pi * 3 / 2, -pi * 3 / 2])
def test_it_wraps_mid_range_angles(theta: float) -> None:
    """It should wrap angles in [-3π/2, -π/2) and (π/2, 3π/2] by subtracting π and adding RX gates."""
    qc = QuantumCircuit(2)
    qc.rxx(theta, 0, 1)

    corrected = theta - copysign(pi, theta)

    expected = QuantumCircuit(2)
    expected.rx(pi, 0)
    expected.rx(pi, 1)

    if corrected >= 0:
        expected.rxx(abs(corrected), 0, 1)
    else:
        expected.rz(pi, 0)
        expected.rxx(abs(corrected), 0, 1)
        expected.rz(pi, 0)

    out = run_pass(qc)
    assert_circuits_equivalent(out, expected)


@pytest.mark.parametrize("theta", [2 * pi, pi * 5 / 2, -pi * 5 / 2])
def test_it_wraps_large_angles(theta: float) -> None:
    """It should wrap angles with absolute value > 3π/2 by modulo 2π and then applying the mid-range angle logic."""
    qc = QuantumCircuit(2)
    qc.rxx(theta, 0, 1)

    wrapped = theta % (2 * pi)
    corrected = wrapped - copysign(2 * pi, wrapped) if abs(wrapped) > 3 * pi / 2 else wrapped

    expected = QuantumCircuit(2)

    if corrected >= 0:
        expected.rxx(abs(corrected), 0, 1)
    else:
        expected.rz(pi, 0)
        expected.rxx(abs(corrected), 0, 1)
        expected.rz(pi, 0)

    out = run_pass(qc)
    assert_circuits_equivalent(out, expected)
