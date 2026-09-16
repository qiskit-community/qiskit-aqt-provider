# This code is part of Qiskit.
#
# (C) Copyright Alpine Quantum Technologies GmbH 2023
#
# This code is licensed under the Apache License, Version 2.0. You may
# obtain a copy of this license in the LICENSE.txt file in the root directory
# of this source tree or at [http://www.apache.org/licenses/LICENSE-2.0](http://www.apache.org/licenses/LICENSE-2.0).
#
# Any modifications or derivative works of this code must retain this
# copyright notice, and modified files need to carry a notice indicating
# that they have been altered from the originals.

import pytest
from qiskit import QuantumCircuit
from qiskit.circuit.library import quantum_volume
from qiskit.converters import circuit_to_dag, dag_to_circuit
from qiskit.transpiler.exceptions import TranspilerError

from qiskit_aqt_provider.transpiler_plugin import (
    EnsureSingleFinalMeasurement,
)


def test_measurements_at_end_are_preserved() -> None:
    """It should preserve single measurements at the end of a circuit."""
    qc = QuantumCircuit(2)
    qc.h(0)
    qc.h(1)
    qc.measure_all()

    dag = circuit_to_dag(qc)
    new_dag = EnsureSingleFinalMeasurement().run(dag)
    new_qc = dag_to_circuit(new_dag)

    assert new_qc.data[-1].operation.name == "measure"


def test_duplicate_measurements_removed() -> None:
    """It should reduce multiple measurements at the end to a single measurement for each qubit."""
    qc = QuantumCircuit(3)
    qc.measure_all()
    qc.measure(0, 0)
    qc.measure(1, 1)
    qc.measure(1, 1)
    qc.measure(2, 2)
    qc.measure_all()
    qc.measure(2, 2)

    dag = circuit_to_dag(qc)
    new_qc = dag_to_circuit(EnsureSingleFinalMeasurement().run(dag))

    measures = [inst for inst in new_qc.data if inst.operation.name == "measure"]
    assert len(measures) == 3


def test_mid_circuit_measurement_raises() -> None:
    """It should raise if there is a mid-circuit measurement."""
    qc = QuantumCircuit(2)
    qc.h(0)
    qc.measure_all()
    qc.h(1)

    dag = circuit_to_dag(qc)

    with pytest.raises(TranspilerError):
        EnsureSingleFinalMeasurement().run(dag)


def test_barriers_after_measurement_removed() -> None:
    """It should remove barriers after the final measurement."""
    qc = QuantumCircuit(2)
    qc.barrier()
    qc.measure_all()
    qc.barrier()

    dag = circuit_to_dag(qc)
    new_qc = dag_to_circuit(EnsureSingleFinalMeasurement().run(dag))

    assert new_qc.data[-1].operation.name == "measure"


def test_rebuild_dag_uses_bits_from_new_dag() -> None:
    """It should rebuild operations with bits belonging to the rebuilt DAG."""
    qc = quantum_volume(5)
    qc.measure_all()

    dag = circuit_to_dag(qc)
    new_dag = EnsureSingleFinalMeasurement().run(dag)
    new_qc = dag_to_circuit(new_dag)

    measures = [inst for inst in new_qc.data if inst.operation.name == "measure"]
    assert len(measures) == new_qc.num_qubits
