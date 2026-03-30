import uuid

import pytest
from aqt_connector import ArnicaApp
from aqt_connector.models.arnica.response_bodies.jobs import (
    JobState,
    RRCancelled,
    RRError,
    RRFinished,
    RROngoing,
    RRQueued,
)

from test.integration.cloud.job._helpers import JOB_ID, make_job, single_qubit_circuit, two_qubit_circuit


def test_result_returns_successful_qiskit_result_for_finished_job(monkeypatch: pytest.MonkeyPatch) -> None:
    """It returns a successful Result payload when the fetched final state is finished."""
    finished_state = RRFinished(result={0: [[0], [1], [1]]})

    def _fetch_job_state(_: ArnicaApp, __: uuid.UUID) -> JobState:
        return finished_state

    monkeypatch.setattr("aqt_connector.fetch_job_state", _fetch_job_state)
    job = make_job(initial_state=RRQueued(), shots=3)

    result = job.result()

    assert result.success
    assert result.job_id == str(JOB_ID)
    assert result.backend_name == "r1"
    assert result.get_counts() == {"0": 1, "1": 2}


def test_result_returns_error_result_for_failed_job(monkeypatch: pytest.MonkeyPatch) -> None:
    """It returns an unsuccessful Result payload and includes the backend error message."""
    error_state = RRError(message="backend failed")

    def _fetch_job_state(_: ArnicaApp, __: uuid.UUID) -> JobState:
        return error_state

    monkeypatch.setattr("aqt_connector.fetch_job_state", _fetch_job_state)
    job = make_job(initial_state=RRQueued(), shots=3)

    result = job.result()

    assert not result.success
    assert result.to_dict()["error"] == "backend failed"
    assert result.results == []


def test_result_returns_unsuccessful_result_for_cancelled_job(monkeypatch: pytest.MonkeyPatch) -> None:
    """It returns an unsuccessful result with no payload entries for cancelled jobs."""
    cancelled_state = RRCancelled()

    def _fetch_job_state(_: ArnicaApp, __: uuid.UUID) -> JobState:
        return cancelled_state

    monkeypatch.setattr("aqt_connector.fetch_job_state", _fetch_job_state)
    job = make_job(initial_state=RRQueued(), shots=3)

    result = job.result()

    assert not result.success
    assert result.results == []
    assert result.to_dict()["error"] is None


def test_result_polls_until_finished_and_uses_latest_state(monkeypatch: pytest.MonkeyPatch) -> None:
    """It polls status repeatedly until finished and then builds the successful result from the final state."""
    calls = 0
    states: list[JobState] = [
        RRQueued(),
        RROngoing(finished_count=0),
        RRFinished(result={0: [[0], [1], [1]]}),
    ]

    def _fetch_job_state(_: ArnicaApp, __: uuid.UUID) -> JobState:
        nonlocal calls
        state = states[min(calls, len(states) - 1)]
        calls += 1
        return state

    # Avoid real sleeping while still exercising JobV1.wait_for_final_state polling behavior.
    monkeypatch.setattr("qiskit.providers.job.time.sleep", lambda _: None)
    monkeypatch.setattr("aqt_connector.fetch_job_state", _fetch_job_state)
    job = make_job(initial_state=RRQueued(), shots=3)

    result = job.result()

    assert calls == 3
    assert result.success
    assert result.get_counts() == {"0": 1, "1": 2}


def test_result_aggregates_multiple_circuits_in_order(monkeypatch: pytest.MonkeyPatch) -> None:
    """It aggregates per-circuit samples into per-circuit Qiskit results in index order."""
    finished_state = RRFinished(
        result={
            0: [[0], [1], [1]],
            1: [[1, 0], [1, 0], [0, 1]],
        }
    )

    def _fetch_job_state(_: ArnicaApp, __: uuid.UUID) -> JobState:
        return finished_state

    monkeypatch.setattr("aqt_connector.fetch_job_state", _fetch_job_state)
    job = make_job(
        initial_state=RRQueued(),
        shots=3,
        circuits=[single_qubit_circuit(), two_qubit_circuit()],
    )

    result = job.result()

    assert result.success
    assert result.get_counts(0) == {"0": 1, "1": 2}
    assert result.get_counts(1) == {"10": 1, "01": 2}
