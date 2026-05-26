import uuid

import pytest
from qiskit.result import Result

from qiskit_aqt_provider.api_client.models_direct import JobResultError, JobResultFinished
from qiskit_aqt_provider.exceptions import AQTJobFailedError
from test.acceptance import dsl
from test.acceptance.conftest import DummyDirectAccessServer


def test_submit_single_native_circuit(direct_access_api: DummyDirectAccessServer) -> None:
    """Submitting a single native circuit should succeed and return the expected job ID.

    Given a reachable direct-access backend
    When a valid native single circuit is submitted
    Then submission succeeds and returns a stable UUID job ID
    """
    job = dsl.user.submits_direct_access_circuit(
        direct_access_api.base_url,
        "direct_token",
        dsl.user.native_circuit(num_qubits=1),
        shots=9,
    )

    assert uuid.UUID(job.job_id(), version=4)  # Validates that the job ID is a valid UUIDv4


def test_fetch_result_for_single_circuit(direct_access_api: DummyDirectAccessServer) -> None:
    """Fetching the result for a single circuit should return the expected output.

    Given a submitted native single-circuit job
    When the result is requested
    Then the expected measurement counts are returned
    """
    job = dsl.user.submits_direct_access_circuit(
        direct_access_api.base_url,
        "direct_token",
        dsl.user.native_circuit(num_qubits=1),
        shots=3,
    )

    dsl.direct_access_resource.will_return_results(direct_access_api, [JobResultFinished(result=[[0], [1], [1]])])

    result = job.result()

    assert isinstance(result, Result)
    assert result.get_counts() == {"0": 1, "1": 2}


def test_failure_in_single_circuit_is_surfaced(direct_access_api: DummyDirectAccessServer) -> None:
    """An error should be raised if the single submitted circuit fails.

    Given a submitted single-circuit job that fails on the backend
    When the result is requested
    Then the failure is surfaced as a direct-access job error
    """
    job = dsl.user.submits_direct_access_circuit(
        direct_access_api.base_url,
        "direct_token",
        dsl.user.native_circuit(num_qubits=1),
    )

    dsl.direct_access_resource.will_return_results(direct_access_api, [JobResultError()])

    with pytest.raises(AQTJobFailedError, match="Job failed with error"):
        job.result()
