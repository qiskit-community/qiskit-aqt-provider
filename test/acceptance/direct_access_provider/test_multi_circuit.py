from typing import Any, cast

import httpx
import pytest
from qiskit.providers.jobstatus import JobStatus

from qiskit_aqt_provider.api_client.models_direct import JobResultError, JobResultFinished
from qiskit_aqt_provider.exceptions import AQTJobFailedError
from test.acceptance import dsl
from test.acceptance.conftest import DummyDirectAccessServer


def test_submit_multiple_circuits_sequentially(direct_access_api: DummyDirectAccessServer) -> None:
    """Submitting multiple circuits sequentially should succeed.

    Given multiple native circuits submitted as one run call
    When the composite result is requested
    Then all constituent circuits are submitted to the API sequentially
    """
    dsl.direct_access_resource.will_return_results(
        direct_access_api,
        [
            JobResultFinished(result=[[0]]),
            JobResultFinished(result=[[1]]),
            JobResultFinished(result=[[0]]),
        ],
    )
    job = dsl.user.submits_direct_access_circuits(
        direct_access_api.base_url,
        "direct_token",
        [dsl.user.native_circuit() for _ in range(3)],
    )

    result = job.result()
    requests = direct_access_api.get_recorded_requests()
    submit_paths = [r["path"] for r in requests if r["method"] == "PUT" and r["path"] == "/circuit"]
    result_paths = [r["path"] for r in requests if r["method"] == "GET" and r["path"].startswith("/circuit/result/")]

    assert len(result.results) == 3
    assert len(submit_paths) == 3
    assert len(result_paths) == 3

    submission_and_result_events = [
        (
            request["method"],
            "/circuit/result" if request["path"].startswith("/circuit/result/") else request["path"],
        )
        for request in requests
        if (request["method"] == "PUT" and request["path"] == "/circuit")
        or (request["method"] == "GET" and request["path"].startswith("/circuit/result/"))
    ]
    assert submission_and_result_events == [
        ("PUT", "/circuit"),
        ("GET", "/circuit/result"),
        ("PUT", "/circuit"),
        ("GET", "/circuit/result"),
        ("PUT", "/circuit"),
        ("GET", "/circuit/result"),
    ]


def test_multiple_results_aggregated_in_input_order(direct_access_api: DummyDirectAccessServer) -> None:
    """Results from multiple circuits should be aggregated in the order they were submitted.

    Given deterministic backend results for each submitted circuit
    When the composite result is retrieved
    Then experiment results preserve input circuit ordering
    """
    dsl.direct_access_resource.will_return_results(
        direct_access_api,
        [
            JobResultFinished(result=[[0], [0]]),
            JobResultFinished(result=[[1], [1]]),
        ],
    )
    job = dsl.user.submits_direct_access_circuits(
        direct_access_api.base_url,
        "direct_token",
        [dsl.user.native_circuit(), dsl.user.native_circuit()],
        shots=2,
    )

    result = job.result()

    assert result.get_counts(0) == {"0": 2}
    assert result.get_counts(1) == {"1": 2}


def test_composite_status_is_initializing_before_submission(
    direct_access_api: DummyDirectAccessServer,
) -> None:
    """Before any of the circuits are submitted, the composite job should report INITIALIZING status.

    Given a just-created composite direct-access job
    When status is queried before result retrieval starts
    Then the job reports INITIALIZING
    """
    job = dsl.user.submits_direct_access_circuits(
        direct_access_api.base_url,
        "direct_token",
        [dsl.user.native_circuit(), dsl.user.native_circuit()],
    )

    assert job.status() == JobStatus.INITIALIZING


def test_composite_status_is_finished_when_all_circuits_succeed(
    direct_access_api: DummyDirectAccessServer,
) -> None:
    """The composite job status should be finished if all circuits succeed.

    Given a composite job where all circuits finish successfully
    When result retrieval completes
    Then status is DONE
    """
    dsl.direct_access_resource.will_return_results(
        direct_access_api,
        [
            JobResultFinished(result=[[0]]),
            JobResultFinished(result=[[1]]),
        ],
    )
    job = dsl.user.submits_direct_access_circuits(
        direct_access_api.base_url,
        "direct_token",
        [dsl.user.native_circuit(), dsl.user.native_circuit()],
    )

    job.result()

    assert job.status() == JobStatus.DONE


def test_composite_status_is_error_if_any_circuit_fails(direct_access_api: DummyDirectAccessServer) -> None:
    """The composite job status should be error if any circuit fails.

    Given a composite job with a failed constituent circuit
    When result retrieval is attempted
    Then status transitions to ERROR
    """
    dsl.direct_access_resource.will_return_results(direct_access_api, [JobResultError()])
    job = dsl.user.submits_direct_access_circuits(
        direct_access_api.base_url,
        "direct_token",
        [dsl.user.native_circuit()],
    )

    with pytest.raises(AQTJobFailedError):
        job.result()

    assert job.status() == JobStatus.ERROR


def test_partial_failure_is_surfaced_as_error(direct_access_api: DummyDirectAccessServer) -> None:
    """If one circuit fails, the composite job should raise an error and skip remaining circuits.

    Given three circuits where the second one fails
    When the composite result is requested
    Then the error is raised and the remaining circuits are not submitted
    """
    dsl.direct_access_resource.will_return_results(
        direct_access_api,
        [
            JobResultFinished(result=[[0]]),
            JobResultError(),
            JobResultFinished(result=[[1]]),
        ],
    )
    job = dsl.user.submits_direct_access_circuits(
        direct_access_api.base_url,
        "direct_token",
        [dsl.user.native_circuit() for _ in range(3)],
    )

    with pytest.raises(AQTJobFailedError):
        job.result()

    requests = direct_access_api.get_recorded_requests()
    submit_requests = [r for r in requests if r["method"] == "PUT" and r["path"] == "/circuit"]
    result_requests = [r for r in requests if r["method"] == "GET" and r["path"].startswith("/circuit/result/")]
    assert len(submit_requests) == 2
    assert len(result_requests) == 2

    submission_and_result_events = [
        (
            request["method"],
            "/circuit/result" if request["path"].startswith("/circuit/result/") else request["path"],
        )
        for request in requests
        if (request["method"] == "PUT" and request["path"] == "/circuit")
        or (request["method"] == "GET" and request["path"].startswith("/circuit/result/"))
    ]
    assert submission_and_result_events == [
        ("PUT", "/circuit"),
        ("GET", "/circuit/result"),
        ("PUT", "/circuit"),
        ("GET", "/circuit/result"),
    ]


def test_composite_timeout_is_handled_correctly(direct_access_api: DummyDirectAccessServer) -> None:
    """If a timeout occurs while waiting for a circuit result, the composite job should raise a timeout error.

    Given the direct backend takes longer than the configured timeout
    When waiting for a composite result
    Then a timeout exception is raised
    """
    direct_access_api.configure_direct_access(
        queued_results=[{"status": "finished", "result": [[0]]}],
        result_delay_seconds=0.2,
    )
    job = dsl.user.submits_direct_access_circuits(
        direct_access_api.base_url,
        "direct_token",
        [dsl.user.native_circuit()],
    )

    with pytest.raises(httpx.TimeoutException):
        cast(Any, job).result(timeout=0.01)
