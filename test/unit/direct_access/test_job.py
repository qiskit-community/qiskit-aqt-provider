from unittest import mock
from uuid import UUID, uuid4

import pytest
from qiskit.circuit import QuantumCircuit
from qiskit.providers.jobstatus import JobStatus as QiskitJobStatus
from qiskit.result import Result

from qiskit_aqt_provider._direct.api_client import DirectAccessAPIClient
from qiskit_aqt_provider._direct.job import DirectAccessJob, DirectAccessJobMetadata
from qiskit_aqt_provider.api_client import models_direct as api_models_direct
from qiskit_aqt_provider.exceptions import AQTJobFailedError


def test_job_id_returns_string_of_uuid() -> None:
    """job_id() should return the string representation of the UUID passed at construction."""
    job_id = uuid4()
    job = _make_job(job_id=job_id)
    assert job.job_id() == str(job_id)


def test_initial_status_is_running() -> None:
    """A newly created job should report RUNNING status."""
    job = _make_job()
    assert job.status() == QiskitJobStatus.RUNNING


def test_submit_always_raises() -> None:
    """submit() should always raise RuntimeError because submission is done via backend.run()."""
    job = _make_job()
    with pytest.raises(RuntimeError):
        job.submit()


def test_result_calls_await_result_with_correct_job_id() -> None:
    """result() should call await_result on the API client with the job's UUID."""
    job_id = uuid4()
    client = mock.Mock(spec=DirectAccessAPIClient)
    client.await_result.return_value = api_models_direct.JobResult.create_finished(job_id=job_id, result=[[0]])
    job = _make_job(client=client, job_id=job_id)

    job.result()

    client.await_result.assert_called_once()
    called_job_id: UUID = client.await_result.call_args[0][0]
    assert called_job_id == job_id


def test_result_forwards_timeout_to_api_client() -> None:
    """result(timeout=…) should pass the timeout value through to await_result."""
    job_id = uuid4()
    client = mock.Mock(spec=DirectAccessAPIClient)
    client.await_result.return_value = api_models_direct.JobResult.create_finished(job_id=job_id, result=[[0]])
    job = _make_job(client=client, job_id=job_id)

    job.result(timeout=42.0)

    assert client.await_result.call_args.kwargs["timeout"] == 42.0


def test_result_returns_qiskit_result_on_success() -> None:
    """result() should return a Qiskit Result object when the job finishes successfully."""
    job_id = uuid4()
    client = mock.Mock(spec=DirectAccessAPIClient)
    client.await_result.return_value = api_models_direct.JobResult.create_finished(job_id=job_id, result=[[0]])
    job = _make_job(client=client, job_id=job_id)

    result = job.result()

    assert isinstance(result, Result)


def test_result_contains_correct_backend_name() -> None:
    """result() should embed the backend name from metadata in the returned Result."""
    job_id = uuid4()
    client = mock.Mock(spec=DirectAccessAPIClient)
    client.await_result.return_value = api_models_direct.JobResult.create_finished(job_id=job_id, result=[[0]])
    job = _make_job(client=client, job_id=job_id, backend_name="my-device")

    result = job.result()

    assert result.backend_name == "my-device"


def test_result_contains_correct_counts() -> None:
    """result() should include the measurement counts derived from the raw samples."""
    job_id = uuid4()
    client = mock.Mock(spec=DirectAccessAPIClient)
    client.await_result.return_value = api_models_direct.JobResult.create_finished(job_id=job_id, result=[[0], [0]])
    circuit = _make_circuit(num_qubits=1)
    job = _make_job(client=client, job_id=job_id, circuit=circuit, shots=2)

    result = job.result()

    counts = result.get_counts()
    assert counts.get("0", 0) == 2


def test_result_raises_on_error_payload() -> None:
    """result() should raise AQTJobFailedError when the API returns an error payload."""
    job_id = uuid4()
    client = mock.Mock(spec=DirectAccessAPIClient)
    client.await_result.return_value = api_models_direct.JobResult.create_error(job_id=job_id)
    job = _make_job(client=client, job_id=job_id)

    with pytest.raises(AQTJobFailedError):
        job.result()


def test_result_sets_status_to_error_on_failure() -> None:
    """After a failed result() call, status() should return ERROR."""
    job_id = uuid4()
    client = mock.Mock(spec=DirectAccessAPIClient)
    client.await_result.return_value = api_models_direct.JobResult.create_error(job_id=job_id)
    job = _make_job(client=client, job_id=job_id)

    with pytest.raises(AQTJobFailedError):
        job.result()

    assert job.status() == QiskitJobStatus.ERROR


def _make_job(
    *,
    client: mock.Mock = mock.Mock(spec=DirectAccessAPIClient),
    job_id: UUID | None = None,
    backend_name: str = "test-backend",
    shots: int = 1,
    circuit: QuantumCircuit | None = None,
) -> DirectAccessJob:
    if job_id is None:
        job_id = uuid4()
    if circuit is None:
        circuit = _make_circuit()
    metadata = DirectAccessJobMetadata(backend_name=backend_name, shots=shots, circuit=circuit)
    return DirectAccessJob(api_client=client, job_id=job_id, metadata=metadata)


def _make_circuit(num_qubits: int = 1) -> QuantumCircuit:
    qc = QuantumCircuit(num_qubits)
    qc.measure_all()
    return qc
