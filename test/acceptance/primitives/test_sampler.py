from math import pi

import pytest
from qiskit import QuantumCircuit, transpile
from qiskit.circuit import Parameter

from qiskit_aqt_provider.primitives import AQTSampler
from test.acceptance.primitives.spy_backend import SpyBackend


def test_sampler_returns_expected_counts_when_running_single_parameter_set() -> None:
    """Check that the AQTSampler returns expected counts when running a circuit with a single parameter set."""
    backend = SpyBackend()
    sampler = AQTSampler(backend=backend)

    theta = Parameter("θ")
    qc = QuantumCircuit(2)
    qc.rx(theta, 0)
    qc.ry(theta, 0)
    qc.rz(theta, 0)
    qc.rxx(theta, 0, 1)
    qc.measure_all()

    job = sampler.run([(qc, [pi])], shots=100)
    result = job.result()

    counts = result[0].data.meas.get_counts()

    assert counts == {"11": 100}


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
def test_aqt_sampler_transpilation(theta: float) -> None:
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
    backend = SpyBackend()
    sampler = AQTSampler(backend=backend)
    sampler.run([(qc, [theta])]).result()

    # the sampler was only called once
    assert len(backend.run_calls) == 1
    # get the circuit passed to the backend
    ([transpiled_circuit], _) = backend.run_calls[0]

    # compare to the circuit obtained by binding the parameters and transpiling at once
    expected = qc.assign_parameters({theta_param: theta})
    tr_expected = transpile(expected, backend=backend)

    assert transpiled_circuit == tr_expected, f"\nexpected:\n{tr_expected}\nresult:\n{transpiled_circuit}"


def test_sampler_circuit_batching() -> None:
    """Check that a Sampler primitive on an offline simulator can split oversized job batches.

    Regression test for #203.
    """
    qc = QuantumCircuit(2)
    qc.h(0)
    qc.cx(0, 1)
    qc.measure_all()

    backend = SpyBackend()
    sampler = AQTSampler(backend=backend)

    batch_size = backend.max_circuits + 1
    result = sampler.run([qc] * batch_size).result()

    assert len(backend.run_calls) == 2
    assert len(result) == batch_size
