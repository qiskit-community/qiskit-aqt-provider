from math import pi

import pytest
from hypothesis import example, given, settings, strategies
from qiskit import QuantumCircuit, generate_preset_pass_manager

from qiskit_aqt_provider._cloud.resource import CloudResource
from qiskit_aqt_provider.circuit_to_aqt import circuits_to_aqt_job


@pytest.mark.parametrize(("optimization_level"), [0, 1, 2, 3])
def test_transpile_for_cloud_resource_returns_circuits_valid_for_submission(
    dummy_cloud_resource: CloudResource, optimization_level: int
) -> None:
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
    qc.r(8 * pi, 2 * pi, 2)  # This needs to be wrapped/substituted to be valid
    qc.rxx(7 * pi, 0, 1)  # This needs to be wrapped to be valid
    qc.rx(-3 * pi / 2, 1)  # This needs to be changed to R and wrapped to be valid
    qc.measure_all()  # Everything after this needs to be removed to be valid
    qc.barrier()
    qc.measure_all()

    pm = generate_preset_pass_manager(backend=dummy_cloud_resource, optimization_level=optimization_level)
    tqc = pm.run(qc)

    circuits_to_aqt_job([tqc], 1)


@settings(max_examples=10)
@example(angles_pi=[-582.16 / pi])
@given(
    angles_pi=strategies.lists(
        strategies.floats(min_value=-1000.0, max_value=1000.0, allow_nan=False),
        min_size=2,
        max_size=6,
    )
)
@pytest.mark.parametrize("optimization_level", [0, 1, 2, 3])
def test_transpilation_preserves_or_decreases_number_of_rxx_gates(
    dummy_cloud_resource: CloudResource, angles_pi: list[float], optimization_level: int
) -> None:
    """Check that transpilation at least preserves the number of RXX gates."""
    pm = generate_preset_pass_manager(backend=dummy_cloud_resource, optimization_level=optimization_level)
    qc = QuantumCircuit(2)
    for angle_pi in angles_pi:
        qc.rxx(angle_pi * pi, 0, 1)

    tr_qc = pm.run(qc)

    tr_qc_ops = tr_qc.count_ops()

    qc_rxx = qc.count_ops()["rxx"]
    assert set(tr_qc_ops) <= set(dummy_cloud_resource.target.operation_names)
    assert qc_rxx == len(angles_pi)
    assert tr_qc_ops.get("rxx", 0) <= qc_rxx
