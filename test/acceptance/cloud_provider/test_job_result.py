from uuid import UUID

import httpx
import pytest
from aqt_connector import ArnicaApp
from aqt_connector.models.arnica.response_bodies.jobs import (
    JobState,
    RRError,
    RRFinished,
    RROngoing,
    RRQueued,
)
from qiskit import QuantumCircuit
from qiskit.providers.exceptions import JobTimeoutError

from qiskit_aqt_provider._cloud.job_metadata import CloudJobMetadata
from qiskit_aqt_provider.exceptions import AQTJobFailedError
from test.acceptance import dsl


def test_returns_result_for_completed_job(monkeypatch: pytest.MonkeyPatch) -> None:
    """It should return a Result for a completed job."""
    _disable_clocks(monkeypatch)
    dsl.user.has_cloud_access(monkeypatch, "arnica_token")
    job_metadata = CloudJobMetadata(
        job_id=UUID("748576c4-4ddf-4f96-8ff3-0ac7d1e779c7"),
        shots=100,
        backend_name="wurst",
        circuits=[QuantumCircuit()],
        initial_state=RRFinished(result={0: [[0], [1], [1]]}),
    )
    job = dsl.user.has_submitted_cloud_job(job_metadata, _mock_client())

    result = job.result()

    assert result.success is True
    assert result.job_id == job.job_id()
    assert result.get_counts(0) == {"0": 1, "1": 2}


def test_waits_for_non_terminal_job_before_returning_result(monkeypatch: pytest.MonkeyPatch) -> None:
    """It should wait for a non-terminal job to complete before returning a Result."""
    _disable_clocks(monkeypatch)
    dsl.user.has_cloud_access(monkeypatch, "arnica_token")
    job_metadata = CloudJobMetadata(
        job_id=UUID("d26523aa-f467-46ce-81a9-dfdb6b649151"),
        shots=100,
        backend_name="wurst",
        circuits=[QuantumCircuit()],
        initial_state=RRQueued(),
    )
    job = dsl.user.has_submitted_cloud_job(job_metadata, _mock_client())

    states: list[JobState] = [
        RROngoing(finished_count=0),
        RROngoing(finished_count=50),
        RRFinished(result={0: [[0], [1], [1]]}),
    ]
    call_count = 0

    def fetch_job_state_mock(arnica: ArnicaApp, job_id: UUID) -> JobState:  # noqa: ARG001
        nonlocal call_count
        state = states[call_count]
        call_count += 1
        return state

    monkeypatch.setattr("aqt_connector.fetch_job_state", fetch_job_state_mock)

    result = job.result()

    assert result.get_counts(0) == {"0": 1, "1": 2}
    assert call_count == 3


def test_raises_for_failed_terminal_job(monkeypatch: pytest.MonkeyPatch) -> None:
    """It should raise if the job reaches a failed terminal state."""
    _disable_clocks(monkeypatch)
    dsl.user.has_cloud_access(monkeypatch, "arnica_token")
    job_metadata = CloudJobMetadata(
        job_id=UUID("0747b844-67f6-44c8-bbde-9b5f1acab50c"),
        shots=100,
        backend_name="wurst",
        circuits=[],
        initial_state=RRQueued(),
    )
    job = dsl.user.has_submitted_cloud_job(job_metadata, _mock_client())
    monkeypatch.setattr("aqt_connector.fetch_job_state", lambda *_: RRError(message="AQT apologies profusely..."))

    with pytest.raises(AQTJobFailedError, match="Job failed: AQT apologies profusely..."):
        job.result()


def test_timeout_raised_when_job_does_not_reach_final_state(monkeypatch: pytest.MonkeyPatch) -> None:
    """It should raise a timeout error if the job does not reach a final state within the specified timeout."""
    _disable_clocks(monkeypatch)
    dsl.user.has_cloud_access(monkeypatch, "arnica_token")
    job_metadata = CloudJobMetadata(
        job_id=UUID("e09e4f8e-3b88-4a4c-ab7b-907fad6fbd44"),
        shots=100,
        backend_name="wurst",
        circuits=[],
        initial_state=RRQueued(),
    )
    job = dsl.user.has_submitted_cloud_job(job_metadata, _mock_client())
    monkeypatch.setattr("aqt_connector.fetch_job_state", lambda *_: RROngoing(finished_count=0))

    with pytest.raises(JobTimeoutError, match="Timeout while waiting for job e09e4f8e-3b88-4a4c-ab7b-907fad6fbd44."):
        job.result(timeout=5)


def _mock_client() -> httpx.Client:
    def _handler(_: httpx.Request) -> httpx.Response:
        raise RuntimeError("This should not be called in these tests")

    return httpx.Client(transport=httpx.MockTransport(_handler))


class _FakeClock:
    """Deterministic stand-in for time.time/time.sleep used by polling logic."""

    def __init__(self) -> None:
        self.now = 0.0
        self.sleeps: list[float] = []

    def time(self) -> float:
        return self.now

    def sleep(self, seconds: float) -> None:
        self.sleeps.append(seconds)
        self.now += seconds


def _disable_clocks(monkeypatch: pytest.MonkeyPatch) -> _FakeClock:
    """Disable real time.sleep and time.time, replacing them with a fake clock."""
    clock = _FakeClock()
    monkeypatch.setattr("qiskit.providers.job.time.time", clock.time)
    monkeypatch.setattr("qiskit.providers.job.time.sleep", clock.sleep)
    return clock
