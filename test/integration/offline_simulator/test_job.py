import pytest
from qiskit.circuit import QuantumCircuit
from qiskit.providers.jobstatus import JobStatus
from qiskit.result import Result
from qiskit_aer import AerSimulator

from qiskit_aqt_provider._offline_sim.job import OfflineSimulatorJob


def test_submit_always_raises() -> None:
    """submit() should always raise RuntimeError because submission is done via backend.run()."""
    job = _make_job()

    with pytest.raises(RuntimeError):
        job.submit()


def test_status_is_done_after_aer_job_completes() -> None:
    """status() should return DONE once the underlying Aer simulation has finished."""
    job = _make_job()
    job.result()

    assert job.status() == JobStatus.DONE


def test_result_returns_qiskit_result() -> None:
    """result() should return a Qiskit Result object."""
    job = _make_job()

    assert isinstance(job.result(), Result)


def test_result_contains_correct_shot_count() -> None:
    """result() should report the same number of shots that were requested."""
    job = _make_job(shots=7)

    assert job.result().results[0].shots == 7


def test_result_get_counts_for_trivial_circuit() -> None:
    """result() for a ground-state circuit should yield only the all-zeros outcome."""
    circuit = QuantumCircuit(2)
    circuit.measure_all()

    job = _make_job(circuit=circuit, shots=10)

    counts = job.result().get_counts()
    assert counts == {"00": 10}


def test_result_with_multiple_circuits_returns_one_experiment_per_circuit() -> None:
    """result() for a job submitted with multiple circuits should contain one ExperimentResult per circuit."""
    circuits = [_make_circuit(num_qubits=1), _make_circuit(num_qubits=2)]

    job = _make_job(circuit=circuits, shots=3)

    assert len(job.result().results) == 2


def _make_job(
    circuit: QuantumCircuit | list[QuantumCircuit] | None = None,
    *,
    shots: int = 1,
) -> OfflineSimulatorJob:
    if circuit is None:
        circuit = _make_circuit()
    simulator = AerSimulator(method="statevector")
    aer_job = simulator.run(circuit, shots=shots)
    return OfflineSimulatorJob(aer_job)


def _make_circuit(num_qubits: int = 1) -> QuantumCircuit:
    circuit = QuantumCircuit(num_qubits)
    circuit.measure_all()
    return circuit
