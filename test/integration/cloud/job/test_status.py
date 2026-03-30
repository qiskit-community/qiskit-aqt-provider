import uuid
from typing import Optional

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
from qiskit.providers.jobstatus import JobStatus as QiskitJobStatus

from test.integration.cloud.job._helpers import JOB_ID, make_job


@pytest.mark.parametrize(
    ("job_state", "expected_status"),
    [
        (RRQueued(), QiskitJobStatus.QUEUED),
        (RROngoing(finished_count=0), QiskitJobStatus.RUNNING),
        (RRFinished(result={0: [[0], [1], [1]]}), QiskitJobStatus.DONE),
        (RRError(message="backend failed"), QiskitJobStatus.ERROR),
        (RRCancelled(), QiskitJobStatus.CANCELLED),
    ],
)
def test_status_maps_cloud_status_to_qiskit_status(
    monkeypatch: pytest.MonkeyPatch, job_state: JobState, expected_status: QiskitJobStatus
) -> None:
    """It maps AQT job states returned by the API to the corresponding Qiskit status."""
    captured_job_id: Optional[uuid.UUID] = None

    def _fetch_job_state(_: ArnicaApp, job_id: uuid.UUID) -> JobState:
        nonlocal captured_job_id
        captured_job_id = job_id
        return job_state

    monkeypatch.setattr("aqt_connector.fetch_job_state", _fetch_job_state)
    job = make_job(initial_state=RRQueued())

    status = job.status()

    assert status is expected_status
    assert captured_job_id == JOB_ID


def test_status_falls_back_to_queued_for_unknown_state(monkeypatch: pytest.MonkeyPatch) -> None:
    """It falls back to QUEUED when the API returns an unknown status value."""

    class _UnknownState:
        def __init__(self) -> None:
            self.status = "some-new-status"

    def _fetch_job_state(_: ArnicaApp, __: uuid.UUID) -> JobState:
        return _UnknownState()  # type: ignore[return-value]

    monkeypatch.setattr("aqt_connector.fetch_job_state", _fetch_job_state)
    job = make_job(initial_state=RRQueued())

    status = job.status()

    assert status is QiskitJobStatus.QUEUED
