from math import pi

from qiskit import QuantumCircuit, generate_preset_pass_manager

from qiskit_aqt_provider.circuit_to_aqt import circuits_to_aqt_job
from test.integration.helpers import get_dummy_cloud_resource


def test_transpile_for_cloud_resource_returns_circuits_valid_for_submission() -> None:
    """Transpiling for CloudResource backends should create circuits that are valid for submission to the backend."""
    qc = QuantumCircuit(3)
    qc.h(0)
    qc.x(1)
    qc.y(2)
    qc.z(0)
    qc.s(1)
    qc.sdg(2)
    qc.t(0)
    qc.tdg(1)
    qc.rx(pi / 3, 0)
    qc.ry(pi / 4, 1)
    qc.rz(pi / 5, 2)
    qc.u(pi / 2, pi / 3, pi / 4, 0)
    qc.cx(0, 1)
    qc.cz(1, 2)
    qc.swap(0, 2)
    qc.barrier()
    qc.cx(2, 0)
    qc.ry(pi / 7, 2)
    qc.measure_all()
    qc.barrier()
    qc.measure_all()

    pm = generate_preset_pass_manager(backend=get_dummy_cloud_resource(), optimization_level=3)
    tqc = pm.run(qc)

    circuits_to_aqt_job([tqc], 1)
