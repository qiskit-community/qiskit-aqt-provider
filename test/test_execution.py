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
expected."""

from math import pi

import pytest
import qiskit
from qiskit import ClassicalRegister, QuantumCircuit, QuantumRegister
from qiskit_experiments.library import QuantumVolume

from qiskit_aqt_provider.aqt_resource import AQTResource


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


@pytest.mark.parametrize("shots,qubits", [(100, 5), (100, 8)])
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


@pytest.mark.parametrize("shots,qubits", [(100, 3)])
def test_simulator_quantum_volume(
    shots: int, qubits: int, offline_simulator_no_noise: AQTResource
) -> None:
    """Run a qiskit_experiments.library.QuantumVolume job. Check that the noiseless simulator
    has at least quantum volume 2**qubits."""
    experiment = QuantumVolume(list(range(qubits)), offline_simulator_no_noise, trials=100)
    experiment.set_transpile_options(optimization_level=0)
    experiment.set_run_options(shots=shots)
    job = experiment.run()

    result = job.analysis_results("quantum_volume")
    assert result.value == (1 << qubits)
    assert result.extra["success"]
