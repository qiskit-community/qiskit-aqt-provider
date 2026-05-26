from unittest import mock
from uuid import uuid4

import pytest
from aqt_connector.models.circuits import QuantumCircuit as AQTQuantumCircuit
from qiskit.circuit import QuantumCircuit

from qiskit_aqt_provider._direct.api_client import DirectAccessAPIClient
from qiskit_aqt_provider._direct.composite_job import CompositeDirectAccessJob
from qiskit_aqt_provider._direct.job import DirectAccessJob
from qiskit_aqt_provider._direct.resource import DirectAccessResource, DirectAccessResourceConfig
from qiskit_aqt_provider.exceptions import AQTApiError


def test_id_returns_config_name() -> None:
    """The resource's id property should return the name from its configuration."""
    resource = _make_resource(name="my-device")
    assert resource.id == "my-device"


def test_max_circuits_is_50() -> None:
    """The resource's max_circuits property should return 50."""
    resource = _make_resource()
    assert resource.max_circuits == 50


def test_default_shots_is_100() -> None:
    """The resource's default options should have 100 shots."""
    resource = _make_resource()
    assert resource._options.shots == 100


def test_target_num_qubits() -> None:
    """The resource's target should report the correct number of qubits."""
    resource = _make_resource(num_qubits=5)
    assert resource.target.num_qubits == 5


def test_target_contains_rz_gate() -> None:
    """The resource's target should support the RZ gate."""
    resource = _make_resource()
    assert resource.target.instruction_supported("rz", (0,))


def test_target_contains_r_gate() -> None:
    """The resource's target should support the R gate."""
    resource = _make_resource()
    assert resource.target.instruction_supported("r", (0,))


def test_target_contains_rxx_gate() -> None:
    """The resource's target should support the RXX gate."""
    resource = _make_resource()
    assert resource.target.instruction_supported("rxx", (0, 1))


def test_target_contains_measure() -> None:
    """The resource's target should support the measure instruction."""
    resource = _make_resource()
    assert resource.target.instruction_supported("measure", (0,))


def test_run_raises_for_shots_zero() -> None:
    """run() should raise a ValueError when shots is 0."""
    resource = _make_resource()
    with pytest.raises(ValueError, match="Shots must be in the range"):
        resource.run(_make_circuit(), shots=0)


def test_run_raises_for_shots_negative() -> None:
    """run() should raise a ValueError when shots is negative."""
    resource = _make_resource()
    with pytest.raises(ValueError, match="Shots must be in the range"):
        resource.run(_make_circuit(), shots=-1)


def test_run_raises_for_shots_above_max() -> None:
    """run() should raise a ValueError when shots is above the maximum."""
    resource = _make_resource()
    with pytest.raises(ValueError, match="Shots must be in the range"):
        resource.run(_make_circuit(), shots=DirectAccessResource.MAX_SHOTS + 1)


def test_run_accepts_shots_at_lower_boundary() -> None:
    """run() should accept 1 shot, the lower boundary."""
    client = mock.Mock(spec=DirectAccessAPIClient)
    circuit = _make_circuit()
    resource = _make_resource(client=client)

    resource.run(circuit, shots=1)

    assert client.submit_circuit.call_args[0][0].repetitions == 1


def test_run_accepts_shots_at_upper_boundary() -> None:
    """run() should accept shots equal to the maximum."""
    client = mock.Mock(spec=DirectAccessAPIClient)
    circuit = _make_circuit()
    resource = _make_resource(client=client)

    resource.run(circuit, shots=DirectAccessResource.MAX_SHOTS)

    assert client.submit_circuit.call_args[0][0].repetitions == DirectAccessResource.MAX_SHOTS


def test_run_none_shots_uses_default_options() -> None:
    """run() with shots=None should use the default shots from the resource's options."""
    client = mock.Mock(spec=DirectAccessAPIClient)
    circuit = _make_circuit()
    resource = _make_resource(client=client)

    resource.run(circuit)

    assert client.submit_circuit.call_args[0][0].repetitions == 100


def test_run_single_circuit_submits_circuit_to_api() -> None:
    """run() with a single circuit should submit the circuit to the API."""
    client = mock.Mock(spec=DirectAccessAPIClient)
    client.submit_circuit = mock.Mock()
    circuit = _make_circuit(num_qubits=3)
    resource = _make_resource(client=client)

    resource.run(circuit)

    client.submit_circuit.assert_called_once()
    submitted_payload: AQTQuantumCircuit = client.submit_circuit.call_args[0][0]
    assert submitted_payload.number_of_qubits == 3
    assert len(submitted_payload.quantum_circuit.root) == 1
    assert submitted_payload.quantum_circuit.root[0].root.operation == "MEASURE"


def test_run_single_circuit_returns_job_with_id_from_server() -> None:
    """run() with a single circuit should return a DirectAccessJob whose ID matches the server response."""
    client = mock.Mock(spec=DirectAccessAPIClient)
    client.submit_circuit = mock.Mock()
    client.submit_circuit.return_value = uuid4()
    circuit = _make_circuit()
    resource = _make_resource(client=client)

    job = resource.run(circuit)

    assert isinstance(job, DirectAccessJob)
    assert job._job_id == str(client.submit_circuit.return_value)


def test_run_single_circuit_raises_on_http_error() -> None:
    """run() with a single circuit should raise when the server returns an error."""
    client = mock.Mock(spec=DirectAccessAPIClient)
    client.submit_circuit = mock.Mock()
    client.submit_circuit.side_effect = AQTApiError("API error")
    resource = _make_resource(client=client)

    with pytest.raises(AQTApiError):
        resource.run(_make_circuit())


def test_run_multiple_circuits_doesnt_submit_to_api() -> None:
    """run() with multiple circuits should not submit to the API immediately."""
    client = mock.Mock(spec=DirectAccessAPIClient)
    circuits = [_make_circuit(), _make_circuit()]
    resource = _make_resource(client=client, num_qubits=10)

    resource.run(circuits)

    client.submit_circuit.assert_not_called()


def test_run_multiple_circuits_returns_composite_job() -> None:
    """run() with a list of circuits should return a CompositeDirectAccessJob."""
    client = mock.Mock(spec=DirectAccessAPIClient)
    circuits = [_make_circuit(), _make_circuit()]
    resource = _make_resource(client=client, num_qubits=10)

    resource.run(circuits)
    job = resource.run(circuits)

    assert isinstance(job, CompositeDirectAccessJob)


def _make_resource(
    *, client: mock.Mock = mock.Mock(spec=DirectAccessAPIClient), num_qubits: int = 2, name: str = "test-resource"
) -> DirectAccessResource:
    config = DirectAccessResourceConfig(name=name, number_of_ions=num_qubits, client=client)
    return DirectAccessResource(config)


def _make_circuit(num_qubits: int = 1) -> QuantumCircuit:
    qc = QuantumCircuit(num_qubits)
    qc.measure_all()
    return qc
