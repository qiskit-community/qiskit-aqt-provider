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
from math import pi
from typing import Union

import pytest
import qiskit
from qiskit import ClassicalRegister, QiskitError, QuantumCircuit, QuantumRegister, quantum_info
from qiskit.providers import BackendV2
from qiskit.providers.jobstatus import JobStatus
from qiskit.transpiler import TranspilerError
from qiskit_aer import AerProvider, AerSimulator

from qiskit_aqt_provider import AQTProvider
from qiskit_aqt_provider.aqt_resource import AnyAQTResource, AQTResource
from qiskit_aqt_provider.test.circuits import assert_circuits_equivalent
from qiskit_aqt_provider.test.fixtures import MockSimulator
from qiskit_aqt_provider.test.resources import TestResource
from qiskit_aqt_provider.test.timeout import timeout


@pytest.mark.parametrize("shots", [200])
def test_empty_circuit(shots: int, any_offline_simulator_no_noise: AnyAQTResource) -> None:
    """Run an empty circuit."""
    qc = QuantumCircuit(1)
    qc.measure_all()

    job = any_offline_simulator_no_noise.run(qc, shots=shots)
    assert job.result().get_counts() == {"0": shots}


def test_circuit_success_lifecycle() -> None:
    """Go through the lifecycle of a successful single-circuit job.
    Check that the job status visits the states QUEUED, RUNNING, and DONE.
    """
    backend = TestResource(min_queued_duration=0.5, min_running_duration=0.5)
    backend.options.update_options(query_period_seconds=0.1)

    qc = QuantumCircuit(1)
    qc.measure_all()

    job = backend.run(qc)

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

    result = backend.run(qc).result()
    assert result.success is False
    assert backend.error_message == result._metadata["error"]


def test_cancelled_circuit() -> None:
    """Check that cancelled jobs return success = false."""
    backend = TestResource(always_cancel=True)

    qc = QuantumCircuit(1)
    qc.measure_all()

    result = backend.run(qc).result()
    assert result.success is False


@pytest.mark.parametrize("shots", [1, 100, 200])
def test_simple_backend_run(shots: int, any_offline_simulator_no_noise: AnyAQTResource) -> None:
    """Run a simple circuit with `backend.run`."""
    qc = QuantumCircuit(1)
    qc.rx(pi, 0)
    qc.measure_all()

    trans_qc = qiskit.transpile(qc, any_offline_simulator_no_noise)
    job = any_offline_simulator_no_noise.run(trans_qc, shots=shots)

    assert job.result().get_counts() == {"1": shots}


@pytest.mark.parametrize("resource", [MockSimulator(noisy=False), MockSimulator(noisy=True)])
def test_simple_backend_execute_noisy(resource: MockSimulator) -> None:
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
        job = resource.run(qiskit.transpile(qc, backend=resource), shots=shots)
        counts += Counter(job.result().get_counts())

    assert sum(counts.values()) == total_shots

    if resource.with_noise_model:
        assert set(counts.keys()) == {"0", "1"}
        assert counts["0"] < 0.1 * counts["1"]  # very crude
    else:
        assert set(counts.keys()) == {"1"}


@pytest.mark.parametrize("shots", [100])
def test_ancilla_qubits_mapping(shots: int, any_offline_simulator_no_noise: AnyAQTResource) -> None:
    """Run a circuit with two quantum registers, with only one mapped to the classical memory."""
    qr = QuantumRegister(2)
    qr_aux = QuantumRegister(3)
    memory = ClassicalRegister(2)

    qc = QuantumCircuit(qr, qr_aux, memory)
    qc.rx(pi, qr[0])
    qc.ry(pi, qr[1])
    qc.rxx(pi / 2, qr_aux[0], qr_aux[1])
    qc.measure(qr, memory)

    trans_qc = qiskit.transpile(qc, any_offline_simulator_no_noise)
    job = any_offline_simulator_no_noise.run(trans_qc, shots=shots)
    # only two bits in the counts dict because memory has two bits width
    assert job.result().get_counts() == {"11": shots}


@pytest.mark.parametrize("shots", [100])
def test_multiple_classical_registers(
    shots: int, any_offline_simulator_no_noise: AnyAQTResource
) -> None:
    """Run a circuit with the final state mapped to multiple classical registers."""
    qr = QuantumRegister(5)
    memory_a = ClassicalRegister(2)
    memory_b = ClassicalRegister(3)

    qc = QuantumCircuit(qr, memory_a, memory_b)
    qc.rx(pi, qr[0])
    qc.rx(pi, qr[3])
    qc.measure(qr[:2], memory_a)
    qc.measure(qr[2:], memory_b)

    trans_qc = qiskit.transpile(qc, any_offline_simulator_no_noise)
    job = any_offline_simulator_no_noise.run(trans_qc, shots=shots)

    # counts are returned as "memory_b memory_a", msb first
    assert job.result().get_counts() == {"010 01": shots}


@pytest.mark.parametrize("shots", [123])
@pytest.mark.parametrize("memory_opt", [True, False])
def test_get_memory_simple(
    shots: int, memory_opt: bool, any_offline_simulator_no_noise: AnyAQTResource
) -> None:
    """Check that the raw bitstrings can be accessed for each shot via the
    get_memory() method in Qiskit's Result.

    The memory is only accessible if the `memory` option is set.
    """
    qc = QuantumCircuit(2)
    qc.h(0)
    qc.cx(0, 1)
    qc.measure_all()

    result = any_offline_simulator_no_noise.run(
        qiskit.transpile(qc, any_offline_simulator_no_noise), shots=shots, memory=memory_opt
    ).result()

    if memory_opt:
        memory = result.get_memory()

        assert set(memory) == {"11", "00"}
        assert len(memory) == shots
    else:
        with pytest.raises(QiskitError, match=re.compile("no memory", re.IGNORECASE)):
            result.get_memory()


@pytest.mark.parametrize("shots", [123])
def test_get_memory_ancilla_qubits(
    shots: int, any_offline_simulator_no_noise: AnyAQTResource
) -> None:
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

    job = any_offline_simulator_no_noise.run(
        qiskit.transpile(qc, any_offline_simulator_no_noise), shots=shots, memory=True
    )
    memory = job.result().get_memory()

    assert set(memory) == {"11"}
    assert len(memory) == shots


@pytest.mark.parametrize("shots", [123])
def test_get_memory_bit_ordering(
    shots: int, any_offline_simulator_no_noise: AnyAQTResource
) -> None:
    """Check that the bitstrings returned by the results produced by AQT jobs have the same
    bit order as the Qiskit Aer simulators.
    """
    sim = AerSimulator(method="statevector")

    qc = QuantumCircuit(3)
    qc.rx(pi, 0)
    qc.rx(pi, 1)
    qc.measure_all()

    aqt_memory = (
        any_offline_simulator_no_noise.run(
            qiskit.transpile(qc, any_offline_simulator_no_noise), shots=shots, memory=True
        )
        .result()
        .get_memory()
    )
    sim_memory = sim.run(qiskit.transpile(qc, sim), shots=shots, memory=True).result().get_memory()

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
def test_regression_issue_85(backend: BackendV2) -> None:
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

    base_bitstrings = set(backend.run(qiskit.transpile(base, backend)).result().get_counts())
    assert base_bitstrings == {"000", "101"}

    perm_qubits_bitstrings = set(
        backend.run(qiskit.transpile(perm_qubits, backend)).result().get_counts()
    )
    assert perm_qubits_bitstrings == {"000", "101"}

    perm_all_bitstrings = set(
        backend.run(qiskit.transpile(perm_all, backend)).result().get_counts()
    )
    assert perm_all_bitstrings == {"000", "011"}


@pytest.mark.parametrize(("shots", "qubits"), [(100, 5), (100, 8)])
def test_bell_states(
    shots: int, qubits: int, any_offline_simulator_no_noise: AnyAQTResource
) -> None:
    """Create a N qubits Bell state."""
    qc = QuantumCircuit(qubits)
    qc.h(0)
    for qubit in range(1, qubits):
        qc.cx(0, qubit)
    qc.measure_all()

    job = any_offline_simulator_no_noise.run(
        qiskit.transpile(qc, any_offline_simulator_no_noise), shots=shots
    )
    counts = job.result().get_counts()

    assert set(counts.keys()) == {"0" * qubits, "1" * qubits}
    assert sum(counts.values()) == shots


@pytest.mark.parametrize(
    "target_state",
    [
        quantum_info.Statevector.from_label("01"),
        "01",
        1,
        [0, 1, 0, 0],
    ],
)
@pytest.mark.parametrize("optimization_level", range(4))
def test_state_preparation(
    target_state: Union[int, str, quantum_info.Statevector, list[complex]],
    optimization_level: int,
    any_offline_simulator_no_noise: AnyAQTResource,
) -> None:
    """Test the state preparation unitary factory.

    Prepare the state |01> using the different formats accepted by
    `QuantumCircuit.prepare_state`.
    """
    qc = QuantumCircuit(2)
    qc.prepare_state(target_state)
    qc.measure_all()

    shots = 100
    job = any_offline_simulator_no_noise.run(
        qiskit.transpile(qc, any_offline_simulator_no_noise, optimization_level=optimization_level),
        shots=shots,
    )
    counts = job.result().get_counts()

    assert counts == {"01": shots}


@pytest.mark.parametrize("optimization_level", range(4))
def test_state_preparation_single_qubit(
    optimization_level: int, any_offline_simulator_no_noise: AnyAQTResource
) -> None:
    """Test the state preparation unitary factory, targeting a single qubit in the register."""
    qreg = QuantumRegister(4)
    qc = QuantumCircuit(qreg)
    qc.prepare_state(1, qreg[2])
    qc.measure_all()

    shots = 100
    job = any_offline_simulator_no_noise.run(
        qiskit.transpile(qc, any_offline_simulator_no_noise, optimization_level=optimization_level),
        shots=shots,
    )
    counts = job.result().get_counts()

    assert counts == {"0100": shots}


def test_initialize_not_supported(offline_simulator_no_noise: AQTResource) -> None:
    """Verify that `QuantumCircuit.initialize` is not supported.

    #112 adds a note to the user guide indicating that `QuantumCircuit.initialize`
    is not supported. Remove the note if this test fails.
    """
    qc = QuantumCircuit(2)
    qc.x(0)
    qc.initialize("01")
    qc.measure_all()

    with pytest.raises(
        TranspilerError,
        match=re.compile(r"unable to translate the operations in the circuit", re.IGNORECASE),
    ):
        qiskit.transpile(qc, offline_simulator_no_noise)


@pytest.mark.parametrize("optimization_level", range(4))
def test_cswap(optimization_level: int, any_offline_simulator_no_noise: AnyAQTResource) -> None:
    """Verify that CSWAP (Fredkin) gates can be transpiled and executed (in a trivial case)."""
    qc = QuantumCircuit(3)
    qc.prepare_state("101")
    qc.cswap(0, 1, 2)

    trans_qc = qiskit.transpile(
        qc, any_offline_simulator_no_noise, optimization_level=optimization_level
    )
    assert_circuits_equivalent(qc, trans_qc)

    qc.measure_all()
    shots = 200
    job = any_offline_simulator_no_noise.run(
        qiskit.transpile(qc, any_offline_simulator_no_noise, optimization_level=optimization_level),
        shots=shots,
    )
    counts = job.result().get_counts()

    assert counts == {"011": shots}
