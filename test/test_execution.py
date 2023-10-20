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

"""Run various circuits on an offline simulator controlled by an AQTResource.

This tests whether the circuit pre-conditioning and results formatting works as
expected.
"""

import re
import typing
from collections import Counter
from fractions import Fraction
from math import pi
from typing import List

import numpy as np
import pytest
import qiskit
from qiskit import ClassicalRegister, QiskitError, QuantumCircuit, QuantumRegister
from qiskit.providers import Backend
from qiskit.providers.jobstatus import JobStatus
from qiskit.result import Counts
from qiskit_aer import AerProvider, AerSimulator
from qiskit_experiments.library import QuantumVolume

from qiskit_aqt_provider import AQTProvider
from qiskit_aqt_provider.aqt_resource import AQTResource
from qiskit_aqt_provider.test.circuits import qft_circuit
from qiskit_aqt_provider.test.fixtures import MockSimulator
from qiskit_aqt_provider.test.resources import TestResource
from qiskit_aqt_provider.test.timeout import timeout


@pytest.mark.parametrize("shots", [200])
def test_empty_circuit(shots: int, offline_simulator_no_noise: AQTResource) -> None:
    """Run an empty circuit."""
    qc = QuantumCircuit(1)
    qc.measure_all()

    job = qiskit.execute(qc, offline_simulator_no_noise, shots=shots)
    assert job.result().get_counts() == {"0": shots}


def test_circuit_success_lifecycle() -> None:
    """Go through the lifecycle of a successful single-circuit job.
    Check that the job status visits the states QUEUED, RUNNING, and DONE.
    """
    backend = TestResource(min_queued_duration=0.5, min_running_duration=0.5)
    backend.options.update_options(query_period_seconds=0.1)

    qc = QuantumCircuit(1)
    qc.measure_all()

    job = qiskit.execute(qc, backend)

    assert job.status() is JobStatus.QUEUED

    with timeout(2.0):
        while job.status() is JobStatus.QUEUED:
            continue

    assert job.status() is JobStatus.RUNNING

    with timeout(2.0):
        while job.status() is JobStatus.RUNNING:
            continue

    assert job.status() is JobStatus.DONE


def test_error_circuit() -> None:
    """Check that errors in circuits are reported in the `errors` field of the Qiskit
    result metadata, where the keys are the circuit job ids.
    """
    backend = TestResource(always_error=True)
    backend.options.update_options(query_period_seconds=0.1)

    qc = QuantumCircuit(1)
    qc.measure_all()

    result = qiskit.execute(qc, backend).result()
    assert result.success is False
    assert backend.error_message == result._metadata["error"]


def test_cancelled_circuit() -> None:
    """Check that cancelled jobs return success = false."""
    backend = TestResource(always_cancel=True)

    qc = QuantumCircuit(1)
    qc.measure_all()

    result = qiskit.execute(qc, backend).result()
    assert result.success is False


@pytest.mark.parametrize("shots", [1, 100, 200])
def test_simple_backend_run(shots: int, offline_simulator_no_noise: AQTResource) -> None:
    """Run a simple circuit with `backend.run`."""
    qc = QuantumCircuit(1)
    qc.rx(pi, 0)
    qc.measure_all()

    trans_qc = qiskit.transpile(qc, offline_simulator_no_noise)
    job = offline_simulator_no_noise.run(trans_qc, shots=shots)

    assert job.result().get_counts() == {"1": shots}


@pytest.mark.parametrize("shots", [1, 100])
def test_simple_backend_execute(shots: int, offline_simulator_no_noise: AQTResource) -> None:
    """Run two simple circuits with `qiskit.execute()`."""
    qc0 = QuantumCircuit(2)
    qc0.rx(pi, 0)
    qc0.measure_all()

    qc1 = QuantumCircuit(2)
    qc1.rx(pi, 1)
    qc1.measure_all()

    # qiskit.execute calls the transpiler automatically
    job = qiskit.execute([qc0, qc1], backend=offline_simulator_no_noise, shots=shots)
    assert job.result().get_counts() == [{"01": shots}, {"10": shots}]


@pytest.mark.parametrize("backend", [MockSimulator(noisy=False), MockSimulator(noisy=True)])
def test_simple_backend_execute_noisy(backend: MockSimulator) -> None:
    """Execute a simple circuit on a noisy and noiseless backend. Check that the noisy backend
    is indeed noisy.
    """
    qc = QuantumCircuit(1)
    qc.rx(pi, 0)
    qc.measure_all()

    # the single qubit error is around 0.1% so to see at least one error, we need to do more than
    # 1000 shots.
    total_shots = 4000  # take some margin
    shots = 200  # maximum shots per submission
    assert total_shots % shots == 0

    counts: typing.Counter[str] = Counter()
    for _ in range(total_shots // shots):
        job = qiskit.execute(qc, backend=backend, shots=shots)
        counts += Counter(job.result().get_counts())

    assert sum(counts.values()) == total_shots

    if backend.with_noise_model:
        assert set(counts.keys()) == {"0", "1"}
        assert counts["0"] < 0.1 * counts["1"]  # very crude
    else:
        assert set(counts.keys()) == {"1"}


@pytest.mark.parametrize("shots", [100])
def test_ancilla_qubits_mapping(shots: int, offline_simulator_no_noise: AQTResource) -> None:
    """Run a circuit with two quantum registers, with only one mapped to the classical memory."""
    qr = QuantumRegister(2)
    qr_aux = QuantumRegister(3)
    memory = ClassicalRegister(2)

    qc = QuantumCircuit(qr, qr_aux, memory)
    qc.rx(pi, qr[0])
    qc.ry(pi, qr[1])
    qc.rxx(pi / 2, qr_aux[0], qr_aux[1])
    qc.measure(qr, memory)

    trans_qc = qiskit.transpile(qc, offline_simulator_no_noise)
    job = offline_simulator_no_noise.run(trans_qc, shots=shots)
    # only two bits in the counts dict because memory has two bits width
    assert job.result().get_counts() == {"11": shots}


@pytest.mark.parametrize("shots", [100])
def test_multiple_classical_registers(shots: int, offline_simulator_no_noise: AQTResource) -> None:
    """Run a circuit with the final state mapped to multiple classical registers."""
    qr = QuantumRegister(5)
    memory_a = ClassicalRegister(2)
    memory_b = ClassicalRegister(3)

    qc = QuantumCircuit(qr, memory_a, memory_b)
    qc.rx(pi, qr[0])
    qc.rx(pi, qr[3])
    qc.measure(qr[:2], memory_a)
    qc.measure(qr[2:], memory_b)

    trans_qc = qiskit.transpile(qc, offline_simulator_no_noise)
    job = offline_simulator_no_noise.run(trans_qc, shots=shots)

    # counts are returned as "memory_b memory_a", msb first
    assert job.result().get_counts() == {"010 01": shots}


@pytest.mark.parametrize("shots", [123])
@pytest.mark.parametrize("memory_opt", [True, False])
def test_get_memory_simple(
    shots: int, memory_opt: bool, offline_simulator_no_noise: AQTResource
) -> None:
    """Check that the raw bitstrings can be accessed for each shot via the
    get_memory() method in Qiskit's Result.

    The memory is only accessible if the `memory` option is set.
    """
    qc = QuantumCircuit(2)
    qc.h(0)
    qc.cx(0, 1)
    qc.measure_all()

    result = qiskit.execute(qc, offline_simulator_no_noise, shots=shots, memory=memory_opt).result()

    if memory_opt:
        memory = result.get_memory()

        assert set(memory) == {"11", "00"}
        assert len(memory) == shots
    else:
        with pytest.raises(QiskitError, match=re.compile("no memory", re.IGNORECASE)):
            result.get_memory()


@pytest.mark.parametrize("shots", [123])
def test_get_memory_ancilla_qubits(shots: int, offline_simulator_no_noise: AQTResource) -> None:
    """Check that the raw bistrings returned by get_memory() in Qiskit's Result only
    contain the mapped classical bits.
    """
    qr = QuantumRegister(2)
    qr_aux = QuantumRegister(3)
    memory = ClassicalRegister(2)

    qc = QuantumCircuit(qr, qr_aux, memory)
    qc.rx(pi, qr[0])
    qc.ry(pi, qr[1])
    qc.rxx(pi / 2, qr_aux[0], qr_aux[1])
    qc.measure(qr, memory)

    job = qiskit.execute(qc, offline_simulator_no_noise, shots=shots, memory=True)
    memory = job.result().get_memory()

    assert set(memory) == {"11"}
    assert len(memory) == shots


@pytest.mark.parametrize("shots", [123])
def test_get_memory_bit_ordering(shots: int, offline_simulator_no_noise: AQTResource) -> None:
    """Check that the bitstrings returned by the results produced by AQT jobs have the same
    bit order as the Qiskit Aer simulators.
    """
    sim = AerSimulator(method="statevector")

    qc = QuantumCircuit(3)
    qc.rx(pi, 0)
    qc.rx(pi, 1)
    qc.measure_all()

    aqt_memory = (
        qiskit.execute(qc, offline_simulator_no_noise, shots=shots, memory=True)
        .result()
        .get_memory()
    )
    sim_memory = qiskit.execute(qc, sim, shots=shots, memory=True).result().get_memory()

    assert set(sim_memory) == set(aqt_memory)

    # sanity check: bitstrings are no palindromes
    assert not any(bitstring == bitstring[::-1] for bitstring in sim_memory)


@pytest.mark.parametrize(
    "backend",
    [
        pytest.param(
            AQTProvider("token").get_backend("offline_simulator_no_noise"), id="offline-simulator"
        ),
        pytest.param(AerProvider().get_backend("aer_simulator"), id="aer-simulator"),
    ],
)
def test_regression_issue_85(backend: Backend) -> None:
    """Check that qubit and clbit permutations are properly handled by the offline simulators.

    This is a regression test for #85. Check that executing circuits with qubit/clbit
    permutations outputs the same bitstrings on noiseless offline simulators from this
    package and straight from Aer.
    """
    empty_3 = QuantumCircuit(3)
    base = QuantumCircuit(3)
    base.h(0)
    base.cx(0, 2)
    base.measure_all()

    perm_qubits = empty_3.compose(base, qubits=[0, 2, 1])
    perm_all = empty_3.compose(base, qubits=[0, 2, 1], clbits=[0, 2, 1])

    base_bitstrings = set(qiskit.execute(base, backend).result().get_counts())
    assert base_bitstrings == {"000", "101"}

    perm_qubits_bitstrings = set(qiskit.execute(perm_qubits, backend).result().get_counts())
    assert perm_qubits_bitstrings == {"000", "101"}

    perm_all_bitstrings = set(qiskit.execute(perm_all, backend).result().get_counts())
    assert perm_all_bitstrings == {"000", "011"}


@pytest.mark.parametrize(("shots", "qubits"), [(100, 5), (100, 8)])
def test_bell_states(shots: int, qubits: int, offline_simulator_no_noise: AQTResource) -> None:
    """Create a N qubits Bell state."""
    qc = QuantumCircuit(qubits)
    qc.h(0)
    for qubit in range(1, qubits):
        qc.cx(0, qubit)
    qc.measure_all()

    job = qiskit.execute(qc, offline_simulator_no_noise, shots=shots)
    counts = job.result().get_counts()

    assert set(counts.keys()) == {"0" * qubits, "1" * qubits}
    assert sum(counts.values()) == shots


@pytest.mark.parametrize(("shots", "qubits"), [(100, 3)])
def test_simulator_quantum_volume(
    shots: int, qubits: int, offline_simulator_no_noise: AQTResource
) -> None:
    """Run a qiskit_experiments.library.QuantumVolume job. Check that the noiseless simulator
    has at least quantum volume 2**qubits.
    """
    experiment = QuantumVolume(list(range(qubits)), offline_simulator_no_noise, trials=100)
    experiment.set_transpile_options(optimization_level=0)
    experiment.set_run_options(shots=shots)
    job = experiment.run()

    result = job.analysis_results("quantum_volume")
    assert result.value == (1 << qubits)
    assert result.extra["success"]


def test_period_finding_circuit(offline_simulator_no_noise: AQTResource) -> None:
    """Run a period-finding circuit for the function 13**x mod 15 on the offline simulator.

    Do 20 evaluations of the 2-shot procedure and collect results. Check that the correct
    period (4) is found often enough.
    """

    # The function to find the period of
    def f(x: int) -> int:
        return pow(13, x, 15)

    def f_circuit(num_qubits: int) -> QuantumCircuit:
        """Quantum circuit for f(x) = 13^x mod 15."""
        qr_x = QuantumRegister(num_qubits, "x")
        qr_fx = QuantumRegister(4, "f(x)")  # 4 bits are enough to store any modulo 15 value

        qc = QuantumCircuit(qr_x, qr_fx)

        qc.x(qr_fx[0])
        qc.x(qr_fx[2])
        qc.x(qr_x[0])
        qc.ccx(qr_x[0], qr_x[1], qr_fx[0])
        qc.x(qr_x[0])
        qc.ccx(qr_x[0], qr_x[1], qr_fx[1])
        qc.x(qr_x[0])
        qc.x(qr_x[1])
        qc.ccx(qr_x[0], qr_x[1], qr_fx[2])
        qc.x(qr_x[0])
        qc.ccx(qr_x[0], qr_x[1], qr_fx[3])
        qc.x(qr_x[1])

        return qc

    # Period finding circuit
    num_qubits = 8
    qr_x = QuantumRegister(num_qubits, "x")
    qr_fx = QuantumRegister(4, "f(x)")
    cr_x = ClassicalRegister(num_qubits, "c_x")
    qc = QuantumCircuit(qr_x, qr_fx, cr_x)

    # Hadamard gates for x register
    for qubit in range(num_qubits):
        qc.h(qr_x[qubit])

    # Create f(x) and QFT subcircuits, and add them to qc
    qc_f = f_circuit(num_qubits)
    qc_qft = qft_circuit(num_qubits)
    gate_f = qc_f.to_gate(label="f(x)")
    gate_qft = qc_qft.to_gate(label="QFT")
    qc.append(gate_f, range(num_qubits + 4))
    qc.append(gate_qft, range(num_qubits))

    # Measure qubits in x register
    qc.measure(qr_x, cr_x)

    def iteration() -> Counts:
        result = qiskit.execute(qc, offline_simulator_no_noise, shots=2).result()
        return result.get_counts()

    n_attempts = 20
    results: List[bool] = []

    # run the circuits (2 shots) n_attempts times
    # and do the classical post-processing to extract the period of the function f.
    for _ in range(n_attempts):
        try:
            x1, x2 = iteration().int_outcomes().keys()
        except ValueError:  # identical results, skip
            continue

        m = num_qubits // 2

        k1 = Fraction(x1, 2**num_qubits).limit_denominator(2**m - 1)
        k2 = Fraction(x2, 2**num_qubits).limit_denominator(2**m - 1)

        b1 = k1.denominator
        b2 = k2.denominator

        r = int(np.lcm(b1, b2))
        results.append(f(r) == f(0))

    # more than 50% of the attempts were successful
    assert len(results) > n_attempts * 0.5

    # got the right result more than 50% of the successful attempts
    # this is quite loose, but doing more iterations would be annoyingly long on CI
    assert np.count_nonzero(results) > len(results) * 0.5
