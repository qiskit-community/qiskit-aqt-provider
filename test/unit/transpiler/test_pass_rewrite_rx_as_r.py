from math import pi

import pytest
from qiskit import QuantumCircuit
from qiskit.converters import circuit_to_dag, dag_to_circuit

from qiskit_aqt_provider.transpiler_plugin import (
    RewriteRxAsR,
)


def test_the_pass_replaces_rx_with_r() -> None:
    """The pass should replace RX gates with R gates."""
    qc = QuantumCircuit(1)
    qc.rx(-pi / 2, 0)

    dag = circuit_to_dag(qc)
    new_dag = RewriteRxAsR().run(dag)
    new_qc = dag_to_circuit(new_dag)

    assert new_qc.data[0].operation.name == "r"


@pytest.mark.parametrize(
    ("input_theta", "output_theta"),
    [
        (0, 0),
        (-4 * pi, 0.0),
        (8 * pi, 0.0),
        (pi / 6, pi / 6),
        (pi / 2, pi / 2),
        (pi, pi),
        (-pi, pi),
        (-pi / 2, pi / 2),
        (3 * pi / 2, pi / 2),
        (5 * pi / 2, pi / 2),
        (-3 * pi / 2, pi / 2),
        (-7 * pi / 2, pi / 2),
    ],
)
def test_the_pass_wraps_r_theta(input_theta: float, output_theta: float) -> None:
    """The pass should wrap the theta parameter of the R gate to be within [0, pi]."""
    qc = QuantumCircuit(1)
    qc.rx(input_theta, 0)
    dag = circuit_to_dag(qc)

    new_dag = RewriteRxAsR().run(dag)

    theta, _ = dag_to_circuit(new_dag).data[0].operation.params
    assert theta == pytest.approx(output_theta)


@pytest.mark.parametrize(
    ("input_theta", "output_phi"),
    [
        (pi / 4, 0.0),
        (5 / 2 * pi, 0.0),
        (-3 * pi / 2, 0.0),
        (-4 * pi, 0.0),
        (5 / 4 * pi, pi),
        (7 / 2 * pi, pi),
        (-1 / 2 * pi, pi),
        (-13 / 2 * pi, pi),
        (0.0, 0.0),
        (pi, 0.0),
        (-2 * pi, 0.0),
        (-pi, pi),
        (2 * pi, pi),
    ],
)
def test_the_pass_sets_phi_correctly(input_theta: float, output_phi: float) -> None:
    """The pass should set the phi parameter of the R gate correctly."""
    qc = QuantumCircuit(1)
    qc.rx(input_theta, 0)
    dag = circuit_to_dag(qc)

    new_dag = RewriteRxAsR().run(dag)

    _, phi = dag_to_circuit(new_dag).data[0].operation.params
    assert phi == pytest.approx(output_phi)
