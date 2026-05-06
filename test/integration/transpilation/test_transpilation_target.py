from math import pi

import pytest
from qiskit import QiskitError, QuantumCircuit
from qiskit.transpiler import generate_preset_pass_manager

from test.integration.helpers import get_dummy_cloud_resource


def test_cloud_resource_provides_the_correct_transpiler_target() -> None:
    """CloudResource backends should provide a target with the correct gate set and qubit count."""
    target = get_dummy_cloud_resource().target

    assert target is not None
    assert target.operation_names == {"rz", "r", "rxx", "measure"}
    assert target.num_qubits == 12


def test_the_cloud_resource_target_has_full_connectivity() -> None:
    """CloudResource targets should be fully connected."""
    backend = get_dummy_cloud_resource()
    qc = QuantumCircuit(backend.target.num_qubits)
    for i in range(backend.target.num_qubits):
        for j in range(backend.target.num_qubits):
            if i != j:
                qc.rxx(0.5, i, j)
                qc.rxx(0.5, j, i)

    pm = generate_preset_pass_manager(backend=backend, optimization_level=0)
    tqc = pm.run(qc)

    assert tqc is not None
    assert tqc.num_qubits == qc.num_qubits
    assert "swap" not in tqc.count_ops()  # If fully connected, no swap should be inserted


def test_it_transpiles_to_the_correct_gate_set() -> None:
    """QCs should transpile to the correct gate set for CloudResource backends."""
    qc = QuantumCircuit(3)

    # --- 1Q Clifford gates ---
    qc.h(0)
    qc.x(1)
    qc.y(2)
    qc.z(0)
    qc.s(1)
    qc.sdg(2)
    qc.t(0)
    qc.tdg(1)

    # --- Parameterized rotations ---
    qc.rx(pi / 3, 0)
    qc.ry(pi / 4, 1)
    qc.rz(pi / 5, 2)

    # --- General single-qubit unitary ---
    qc.u(pi / 2, pi / 3, pi / 4, 0)

    # --- 2Q entangling gates ---
    qc.cx(0, 1)
    qc.cz(1, 2)
    qc.swap(0, 2)

    # --- Barrier (tests preservation/handling) ---
    qc.barrier()

    # --- More structure to force routing decisions ---
    qc.cx(2, 0)
    qc.ry(pi / 7, 2)

    # --- Measurement ---
    qc.measure_all()

    backend = get_dummy_cloud_resource()
    pm = generate_preset_pass_manager(backend=backend)
    transpiled_qc = pm.run(qc)

    for op in transpiled_qc.count_ops():
        assert op in backend.target.operation_names or op == "barrier"


def test_transpilation_for_target_fails_for_too_many_qubits() -> None:
    """Transpilation for CloudResource backends should fail if the circuit has too many qubits."""
    qc = QuantumCircuit(13)
    qc.rxx(0.5, 0, 12)

    pm = generate_preset_pass_manager(backend=get_dummy_cloud_resource())

    with pytest.raises(QiskitError, match="Target has no gates available on qubits to synthesize over."):
        pm.run(qc)
