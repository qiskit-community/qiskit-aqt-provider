# This code is part of Qiskit.
#
# (C) Alpine Quantum Technologies GmbH 2023.
#
# This code is licensed under the Apache License, Version 2.0. You may
# obtain a copy of this license in the LICENSE.txt file in the root directory
# of this source tree or at http://www.apache.org/licenses/LICENSE-2.0.
#
# Any modifications or derivative works of this code must retain this
# copyright notice, and modified files need to carry a notice indicating
# that they have been altered from the originals.

from math import isclose, pi
from typing import Callable

import pytest
import qiskit
from qiskit.circuit import Parameter, QuantumCircuit
from qiskit.primitives import (
    BackendEstimator,
    BackendSampler,
    BaseEstimatorV1,
    BaseSamplerV1,
    Sampler,
)
from qiskit.providers import Backend, BackendV2
from qiskit.quantum_info import SparsePauliOp
from qiskit.transpiler.exceptions import TranspilerError

from qiskit_aqt_provider.primitives import AQTSampler
from qiskit_aqt_provider.primitives.estimator import AQTEstimator
from qiskit_aqt_provider.test.circuits import assert_circuits_equal
from qiskit_aqt_provider.test.fixtures import MockSimulator


@pytest.fixture(scope="module")
def assert_all_responses_were_requested() -> bool:
    """Disable pytest-httpx check that all mocked responses are used for this module.

    Some tests in this module request the offline_simulator_no_noise_direct_access
    fixture without using it, thus not calling the mocked HTTP responses it contains.

    # TODO: use alternative HTTPXMock setup when available.
    # See: https://github.com/Colin-b/pytest_httpx/issues/137
    """
    return False


def test_backend_primitives_are_v1() -> None:
    """Check that `BackendSampler` and `BackendEstimator` have primitives V1 interfaces.

    As of 2024-02-20, there are no backend primitives that provide V2 interfaces.

    If this test fails, the `AQTSampler` and `AQTEstimator` docs as well as the user
    guide must be updated.

    An interface mismatch may be detected at other spots. This makes the detection explicit.
    """
    assert issubclass(BackendSampler, BaseSamplerV1)
    assert issubclass(BackendEstimator, BaseEstimatorV1)


@pytest.mark.parametrize(
    "get_sampler",
    [
        # Reference implementation
        lambda _: Sampler(),
        # The AQT transpilation plugin doesn't support transpiling unbound parametric circuits
        # and the BackendSampler doesn't fallback to transpiling the bound circuit if
        # transpiling the unbound circuit failed (like the opflow sampler does).
        # Sampling a parametric circuit with the generic BackendSampler is therefore not supported.
        pytest.param(
            lambda backend: BackendSampler(backend), marks=pytest.mark.xfail(raises=TranspilerError)
        ),
        # The specialized implementation of the Sampler primitive for AQT backends delays the
        # transpilation passes that require bound parameters.
        lambda backend: AQTSampler(backend),
    ],
)
def test_circuit_sampling_primitive(
    get_sampler: Callable[[Backend], BaseSamplerV1], any_offline_simulator_no_noise: BackendV2
) -> None:
    """Check that a `Sampler` primitive using an AQT backend can sample parametric circuits."""
    theta = Parameter("θ")

    qc = QuantumCircuit(2)
    qc.rx(theta, 0)
    qc.ry(theta, 0)
    qc.rz(theta, 0)
    qc.rxx(theta, 0, 1)
    qc.measure_all()

    assert qc.num_parameters > 0

    sampler = get_sampler(any_offline_simulator_no_noise)
    sampled = sampler.run(qc, [pi]).result().quasi_dists
    assert sampled == [{3: 1.0}]


@pytest.mark.parametrize("theta", [0.0, pi])
def test_operator_estimator_primitive_trivial_pauli_x(
    theta: float, offline_simulator_no_noise: MockSimulator
) -> None:
    """Use the Estimator primitive to verify that <0|X|0> = <1|X|1> = 0.

    Define the parametrized circuit that consists of the single gate Rx(θ) with
    θ=0,π. Applied to |0>, this creates the states |0>,|1>. The Estimator primitive
    is then used to evaluate the expectation value of the Pauli X operator on the
    state produced by the circuit.
    """
    offline_simulator_no_noise.simulator.options.seed_simulator = 0

    estimator = AQTEstimator(offline_simulator_no_noise, options={"shots": 200})

    qc = QuantumCircuit(1)
    qc.rx(theta, 0)

    op = SparsePauliOp("X")
    result = estimator.run(qc, op).result()

    assert abs(result.values[0]) < 0.1


def test_operator_estimator_primitive_trivial_pauli_z(
    offline_simulator_no_noise: MockSimulator,
) -> None:
    """Use the Estimator primitive to verify that:
    <0|Z|0> = 1
    <1|Z|1> = -1
    <ψ|Z|ψ> = 0 with |ψ> = (|0> + |1>)/√2.

    The sampled circuit is always Rx(θ) with θ=0,π,π/2 respectively.

    The θ values are passed into a single call to the estimator, thus also checking
    that the AQTEstimator can deal with parametrized circuits.
    """
    offline_simulator_no_noise.simulator.options.seed_simulator = 0

    estimator = AQTEstimator(offline_simulator_no_noise, options={"shots": 200})

    theta = Parameter("θ")
    qc = QuantumCircuit(1)
    qc.rx(theta, 0)

    op = SparsePauliOp("Z")
    result = estimator.run([qc] * 3, [op] * 3, [[0], [pi], [pi / 2]]).result()

    z0, z1, z01 = result.values

    assert isclose(z0, 1.0)  # <0|Z|0>
    assert isclose(z1, -1.0)  # <1|Z|1>
    assert abs(z01) < 0.1  # <ψ|Z|ψ>, |ψ> = (|0> + |1>)/√2


@pytest.mark.parametrize(
    "theta",
    [
        pi / 3,
        -pi / 3,
        pi / 2,
        -pi / 2,
        3 * pi / 4,
        -3 * pi / 4,
        15 * pi / 8,
        -15 * pi / 8,
        33 * pi / 16,
        -33 * pi / 16,
    ],
)
def test_aqt_sampler_transpilation(theta: float, offline_simulator_no_noise: MockSimulator) -> None:
    """Check that the AQTSampler passes the same circuit to the backend as a call to
    `backend.run` with the same transpiler call on the bound circuit would.
    """
    theta_param = Parameter("θ")

    # define a circuit with unbound parameters
    qc = QuantumCircuit(2)
    qc.rx(pi / 3, 0)
    qc.rxx(theta_param, 0, 1)
    qc.measure_all()

    assert qc.num_parameters > 0

    # sample the circuit, passing parameter assignments
    sampler = AQTSampler(offline_simulator_no_noise)
    sampler.run(qc, [theta]).result()

    # the sampler was only called once
    assert len(offline_simulator_no_noise.submitted_circuits) == 1
    # get the circuit passed to the backend
    ((transpiled_circuit,),) = offline_simulator_no_noise.submitted_circuits

    # compare to the circuit obtained by binding the parameters and transpiling at once
    expected = qc.assign_parameters({theta_param: theta})
    tr_expected = qiskit.transpile(expected, offline_simulator_no_noise)

    assert_circuits_equal(transpiled_circuit, tr_expected)
