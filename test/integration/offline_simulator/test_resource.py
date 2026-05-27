from qiskit.circuit import QuantumCircuit
from qiskit_aer import AerSimulator

from qiskit_aqt_provider._offline_sim.job import OfflineSimulatorJob
from qiskit_aqt_provider._offline_sim.resource import OfflineSimulatorResource, OfflineSimulatorResourceConfig


def test_run_returns_offline_simulator_job() -> None:
    """run() should return an OfflineSimulatorJob wrapping the Aer execution."""
    resource = _make_resource()

    job = resource.run(_make_circuit(), shots=1)

    assert isinstance(job, OfflineSimulatorJob)


def test_run_result_contains_correct_shot_count() -> None:
    """result() should contain the same number of shots that were requested."""
    resource = _make_resource()

    result = resource.run(_make_circuit(num_qubits=1), shots=7).result()

    assert result.results[0].shots == 7


def test_run_result_returns_deterministic_counts_for_trivial_circuit() -> None:
    """result() for a ground-state circuit with no gates should always yield the all-zeros outcome."""
    resource = _make_resource()
    circuit = QuantumCircuit(2)
    circuit.measure_all()

    result = resource.run(circuit, shots=10).result()

    # The statevector simulator on |00⟩ with no gates always measures "00"
    counts = result.get_counts()
    assert counts == {"00": 10}


def test_run_multiple_circuits_returns_one_result_per_circuit() -> None:
    """run() with a list of circuits should produce one ExperimentResult per circuit."""
    resource = _make_resource()
    circuits = [_make_circuit(num_qubits=1), _make_circuit(num_qubits=1)]

    result = resource.run(circuits, shots=3).result()

    assert len(result.results) == 2


def _make_resource(num_qubits: int = 2) -> OfflineSimulatorResource:
    config = OfflineSimulatorResourceConfig(
        name="integration-sim",
        number_of_ions=num_qubits,
        simulator=AerSimulator(method="statevector"),
    )
    return OfflineSimulatorResource(config=config)


def _make_circuit(num_qubits: int = 2) -> QuantumCircuit:
    circuit = QuantumCircuit(num_qubits)
    circuit.measure_all()
    return circuit
