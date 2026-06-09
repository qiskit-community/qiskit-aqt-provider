from math import isclose, pi

import numpy as np
import pytest
from qiskit import QuantumCircuit
from qiskit.circuit import Parameter
from qiskit.quantum_info import SparsePauliOp

from qiskit_aqt_provider.primitives import AQTEstimator
from test.acceptance.primitives.spy_backend import SpyBackend


@pytest.mark.parametrize("theta", [0.0, pi])
def test_estimator_v2_trivial_pauli_x(theta: float) -> None:
    """Use the Estimator primitive to verify that <0|X|0> = <1|X|1> = 0.

    Define a one-qubit circuit consisting of Rx(theta), with theta=0 and theta=pi.
    Applied to |0>, this prepares |0> and |1>. The Estimator primitive is then used
    to evaluate the expectation value of the Pauli X operator on the produced state.
    """
    backend = SpyBackend()
    backend.simulator.options.seed_simulator = 0
    estimator = AQTEstimator(backend=backend)

    qc = QuantumCircuit(1)
    qc.rx(theta, 0)

    op = SparsePauliOp("X")

    result = estimator.run([(qc, op)], precision=0.1).result()

    evs = np.asarray(result[0].data.evs)

    assert evs.shape == ()
    assert abs(evs.item()) < 0.1


def test_operator_estimator_primitive_trivial_pauli_z() -> None:
    """Use the Estimator primitive to verify that:
    <0|Z|0> = 1
    <1|Z|1> = -1
    <ψ|Z|ψ> = 0 with |ψ> = (|0> + |1>)/√2.

    The sampled circuit is always Rx(theta) with theta=0, pi, pi/2 respectively.

    The theta values are passed into a single estimator PUB, thus also checking
    that the Estimator can deal with parametrized circuits.
    """
    backend = SpyBackend()
    backend.simulator.options.seed_simulator = 0
    estimator = AQTEstimator(backend=backend)

    theta = Parameter("θ")

    qc = QuantumCircuit(1)
    qc.rx(theta, 0)

    op = SparsePauliOp("Z")

    result = estimator.run(
        [
            (
                qc,
                op,
                [[0.0], [pi], [pi / 2]],
            )
        ],
        precision=0.070710678,  # 200 shots
    ).result()

    evs = np.asarray(result[0].data.evs)

    assert evs.shape == (3,)

    z0, z1, z01 = evs

    assert isclose(z0, 1.0, abs_tol=0.1)  # <0|Z|0>
    assert isclose(z1, -1.0, abs_tol=0.1)  # <1|Z|1>
    assert abs(z01) < 0.1  # <ψ|Z|ψ>, |ψ> = (|0> + |1>)/√2
