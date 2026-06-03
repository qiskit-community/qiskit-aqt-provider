from collections.abc import Callable
from unittest import mock
from uuid import UUID, uuid4

import pytest
from qiskit.circuit import QuantumCircuit
from qiskit.providers.jobstatus import JobStatus as QiskitJobStatus
from qiskit.result import Result

from qiskit_aqt_provider._direct.api_client import DirectAccessAPIClient
from qiskit_aqt_provider._direct.composite_job import CompositeDirectAccessJob, CompositeDirectAccessJobMetadata
from qiskit_aqt_provider._direct.job import DirectAccessJob, DirectAccessJobMetadata
from qiskit_aqt_provider.api_client import models_direct as api_models_direct
from qiskit_aqt_provider.exceptions import AQTJobFailedError


def test_submit_always_raises() -> None:
    """submit() should always raise RuntimeError because submission is done via backend.run()."""
    job = _make_composite_job()
    with pytest.raises(RuntimeError):
        job.submit()


def test_initial_status_is_initializing() -> None:
    """A newly created composite job should report INITIALIZING status."""
    job = _make_composite_job()
    assert job.status() == QiskitJobStatus.INITIALIZING


def test_result_with_no_circuits_returns_empty_result() -> None:
    """result() with no submitters should return a Result with no experiment results."""
    job = _make_composite_job(submitters=[])

    result = job.result()

    assert isinstance(result, Result)
    assert result.results == []


def test_status_is_done_after_successful_result() -> None:
    """status() should be DONE after a successful result() call."""
    client = mock.Mock(spec=DirectAccessAPIClient)
    job_id = uuid4()
    client.await_result.return_value = api_models_direct.JobResult.create_finished(job_id=job_id, result=[[0]]).payload
    job = _make_composite_job(submitters=[_make_submitter(client, job_id=job_id)])

    job.result()

    assert job.status() == QiskitJobStatus.DONE


def test_result_returns_qiskit_result() -> None:
    """result() should return a Qiskit Result object."""
    client = mock.Mock(spec=DirectAccessAPIClient)
    job_id = uuid4()
    client.await_result.return_value = api_models_direct.JobResult.create_finished(job_id=job_id, result=[[0]]).payload
    job = _make_composite_job(submitters=[_make_submitter(client, job_id=job_id)])

    assert isinstance(job.result(), Result)


def test_result_contains_correct_backend_name() -> None:
    """result() should embed the backend name from metadata in the returned Result."""
    client = mock.Mock(spec=DirectAccessAPIClient)
    job_id = uuid4()
    client.await_result.return_value = api_models_direct.JobResult.create_finished(job_id=job_id, result=[[0]]).payload
    job = _make_composite_job(backend_name="my-device", submitters=[_make_submitter(client, job_id=job_id)])

    assert job.result().backend_name == "my-device"


def test_result_calls_each_submitter_once() -> None:
    """result() should invoke each submitter callable exactly once."""
    client = mock.Mock(spec=DirectAccessAPIClient)
    client.await_result.return_value = api_models_direct.JobResult.create_finished(job_id=uuid4(), result=[[0]]).payload

    submitter_a = mock.Mock(return_value=_make_job(client=client))
    submitter_b = mock.Mock(return_value=_make_job(client=client))
    job = _make_composite_job(submitters=[submitter_a, submitter_b])

    job.result()

    submitter_a.assert_called_once()
    submitter_b.assert_called_once()


def test_result_calls_await_result_for_each_circuit() -> None:
    """result() should call await_result on the API client once per circuit."""
    client = mock.Mock(spec=DirectAccessAPIClient)
    client.await_result.return_value = api_models_direct.JobResult.create_finished(job_id=uuid4(), result=[[0]]).payload
    job = _make_composite_job(submitters=[_make_submitter(client), _make_submitter(client)])

    job.result()

    assert client.await_result.call_count == 2


def test_result_contains_one_experiment_per_circuit() -> None:
    """result() should include one ExperimentResult per submitted circuit."""
    client = mock.Mock(spec=DirectAccessAPIClient)
    client.await_result.return_value = api_models_direct.JobResult.create_finished(job_id=uuid4(), result=[[0]]).payload
    job = _make_composite_job(submitters=[_make_submitter(client), _make_submitter(client)])

    result = job.result()

    assert len(result.results) == 2


def test_result_raises_when_a_circuit_fails() -> None:
    """result() should raise AQTJobFailedError if any circuit fails."""
    client = mock.Mock(spec=DirectAccessAPIClient)
    job_id = uuid4()
    client.await_result.return_value = api_models_direct.JobResult.create_error(job_id=job_id).payload
    job = _make_composite_job(submitters=[_make_submitter(client, job_id=job_id)])

    with pytest.raises(AQTJobFailedError):
        job.result()


def test_result_sets_status_to_error_on_failure() -> None:
    """status() should be ERROR after a failed result() call."""
    client = mock.Mock(spec=DirectAccessAPIClient)
    job_id = uuid4()
    client.await_result.return_value = api_models_direct.JobResult.create_error(job_id=job_id).payload
    job = _make_composite_job(submitters=[_make_submitter(client, job_id=job_id)])

    with pytest.raises(AQTJobFailedError):
        job.result()

    assert job.status() == QiskitJobStatus.ERROR


def test_result_skips_remaining_circuits_after_failure() -> None:
    """result() should not invoke remaining submitters after the first circuit fails."""
    client = mock.Mock(spec=DirectAccessAPIClient)
    failing_job_id = uuid4()
    client.await_result.return_value = api_models_direct.JobResult.create_error(job_id=failing_job_id).payload

    second_submitter = mock.Mock()
    job = _make_composite_job(submitters=[_make_submitter(client, job_id=failing_job_id), second_submitter])

    with pytest.raises(AQTJobFailedError):
        job.result()

    second_submitter.assert_not_called()


def test_result_forwards_timeout_to_each_job() -> None:
    """result(timeout=…) should forward the timeout value to each individual job's await_result call."""
    client = mock.Mock(spec=DirectAccessAPIClient)
    client.await_result.return_value = api_models_direct.JobResult.create_finished(job_id=uuid4(), result=[[0]]).payload
    job = _make_composite_job(submitters=[_make_submitter(client), _make_submitter(client)])

    job.result(timeout=99.0)

    for call in client.await_result.call_args_list:
        assert call.kwargs["timeout"] == 99.0


def _make_composite_job(
    *,
    backend_name: str = "test-backend",
    submitters: list[Callable[[], DirectAccessJob]] | None = None,
) -> CompositeDirectAccessJob:
    metadata = CompositeDirectAccessJobMetadata(backend_name=backend_name)
    return CompositeDirectAccessJob(metadata=metadata, job_submitters=submitters or [])


def _make_submitter(client: mock.Mock, *, job_id: UUID | None = None) -> Callable[[], DirectAccessJob]:
    if job_id is None:
        job_id = uuid4()
    captured_id = job_id
    return lambda: _make_job(client=client, job_id=captured_id)


def _make_job(
    *,
    client: mock.Mock,
    job_id: UUID | None = None,
    backend_name: str = "test-backend",
    shots: int = 1,
) -> DirectAccessJob:
    if job_id is None:
        job_id = uuid4()
    metadata = DirectAccessJobMetadata(backend_name=backend_name, shots=shots, circuit=_make_circuit(), memory=False)
    return DirectAccessJob(api_client=client, job_id=job_id, metadata=metadata)


def _make_circuit(num_qubits: int = 1) -> QuantumCircuit:
    qc = QuantumCircuit(num_qubits)
    qc.measure_all()
    return qc
