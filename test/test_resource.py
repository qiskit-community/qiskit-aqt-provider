# This code is part of Qiskit.
#
# (C) Copyright IBM 2019, Alpine Quantum Technologies GmbH 2023.
#
# This code is licensed under the Apache License, Version 2.0. You may
# obtain a copy of this license in the LICENSE.txt file in the root directory
# of this source tree or at http://www.apache.org/licenses/LICENSE-2.0.
#
# Any modifications or derivative works of this code must retain this
# copyright notice, and modified files need to carry a notice indicating
# that they have been altered from the originals.

import math
import uuid
from unittest import mock

import httpx
import pytest
from pytest_httpx import HTTPXMock
from qiskit import QuantumCircuit
from qiskit.providers.exceptions import JobTimeoutError

from qiskit_aqt_provider.aqt_job import AQTJob
from qiskit_aqt_provider.aqt_provider import AQTProvider
from qiskit_aqt_provider.aqt_resource import (
    ApiResource,
    AQTResource,
    OfflineSimulatorResource,
)
from qiskit_aqt_provider.test.circuits import empty_circuit
from qiskit_aqt_provider.test.fixtures import MockSimulator
from qiskit_aqt_provider.test.resources import DummyResource, TestResource


def test_options_set_query_timeout(offline_simulator_no_noise: AQTResource) -> None:
    """Set the query timeout for job status queries with different values."""
    backend = offline_simulator_no_noise

    # works with integers
    backend.options.update_options(query_timeout_seconds=123)
    assert backend.options.query_timeout_seconds == 123

    # works with floats
    backend.options.update_options(query_timeout_seconds=123.45)
    assert backend.options.query_timeout_seconds == 123.45

    # works with None (no timeout)
    backend.options.update_options(query_timeout_seconds=None)
    assert backend.options.query_timeout_seconds is None

    # doesn't work with str
    with pytest.raises(TypeError):
        backend.options.update_options(query_timeout_seconds="abc")


def test_options_set_query_period(offline_simulator_no_noise: AQTResource) -> None:
    """Set the query period for job status queries with different values."""
    backend = offline_simulator_no_noise

    # works with integers
    backend.options.update_options(query_period_seconds=123)
    assert backend.options.query_period_seconds == 123

    # works with floats
    backend.options.update_options(query_period_seconds=123.45)
    assert backend.options.query_period_seconds == 123.45

    # doesn't work with None
    with pytest.raises(TypeError):
        backend.options.update_options(query_period_seconds=None)

    # doesn't work with str
    with pytest.raises(TypeError):
        backend.options.update_options(query_period_seconds="abc")


def test_query_timeout_propagation() -> None:
    """Check that the query timeout is properly propagated from the backend options to
    the job result polling loop.

    Acquire a resource with 10s processing time, but set the job result timeout to 1s.
    Check that calling `result()` on the job handle fails with a timeout error.
    """
    response_delay = 10.0
    timeout = 1.0
    assert timeout < response_delay

    backend = TestResource(min_running_duration=response_delay)
    backend.options.update_options(query_timeout_seconds=timeout, query_period_seconds=0.5)

    qc = QuantumCircuit(1)
    qc.rx(3.14, 0)

    job = backend.run(qc)

    with pytest.raises(JobTimeoutError):
        job.result()


def test_query_period_propagation() -> None:
    """Check that the query wait duration is properly propagated from the backend options
    to the job result polling loop.

    Set the polling period (much) shorter than the backend's processing time. Check that
    the backend is polled the calculated number of times.
    """
    response_delay = 2.0
    period_seconds = 0.5
    timeout_seconds = 3.0
    assert timeout_seconds > response_delay  # won't time out

    backend = TestResource(min_running_duration=response_delay)
    backend.options.update_options(
        query_timeout_seconds=timeout_seconds, query_period_seconds=period_seconds
    )

    qc = QuantumCircuit(1)
    qc.rx(3.14, 0)
    qc.measure_all()

    job = backend.run(qc)

    with mock.patch.object(AQTJob, "status", wraps=job.status) as mocked_status:
        job.result()

    lower_bound = math.floor(response_delay / period_seconds)
    upper_bound = math.ceil(response_delay / period_seconds) + 1
    assert lower_bound <= mocked_status.call_count <= upper_bound


def test_offline_simulator_invalid_api_resource() -> None:
    """Check that one cannot instantiate an OfflineSimulatorResource on an API resource
    that is no offline simulator.
    """
    with pytest.raises(ValueError):
        OfflineSimulatorResource(
            AQTProvider(""),
            "default",
            ApiResource(name="dummy", id="dummy", type="device"),
        )


def test_submit_valid_response(httpx_mock: HTTPXMock) -> None:
    """Check that AQTResource.submit passes the authorization token and
    extracts the correct job_id when the response payload is valid.
    """
    token = str(uuid.uuid4())
    backend = DummyResource(token)
    expected_job_id = str(uuid.uuid4())

    def handle_submit(request: httpx.Request) -> httpx.Response:
        assert request.headers["sdk"] == "qiskit"
        assert request.headers["authorization"] == f"Bearer {token}"

        return httpx.Response(
            status_code=httpx.codes.OK,
            json={
                "job": {
                    "job_id": expected_job_id,
                    "job_type": "quantum_circuit",
                    "label": "Example computation",
                    "resource_id": backend._resource["id"],
                    "workspace_id": backend._workspace,
                },
                "response": {"status": "queued"},
            },
        )

    httpx_mock.add_callback(handle_submit, method="POST")

    job_id = backend.submit(empty_circuit(2), shots=10)
    assert job_id == expected_job_id


def test_submit_bad_request(httpx_mock: HTTPXMock) -> None:
    """Check that AQTResource.submit raises an HTTPError if the request
    is flagged invalid by the server.
    """
    backend = DummyResource("")
    httpx_mock.add_response(status_code=httpx.codes.BAD_REQUEST)

    with pytest.raises(httpx.HTTPError):
        backend.submit(empty_circuit(2), shots=10)


def test_submit_bad_payload_no_job(httpx_mock: HTTPXMock) -> None:
    """Check that AQTResource.submit raises a ValueError if the returned
    payload does not contain a job field.
    """
    backend = DummyResource("")
    httpx_mock.add_response(json={})

    with pytest.raises(ValueError, match=r"^API response does not contain field"):
        backend.submit(empty_circuit(2), shots=10)


def test_submit_bad_payload_no_jobid(httpx_mock: HTTPXMock) -> None:
    """Check that AQTResource.submit raises a ValueError if the returned
    payload does not contain a job.job_id field.
    """
    backend = DummyResource("")
    httpx_mock.add_response(json={"job": {}})

    with pytest.raises(ValueError, match=r"^API response does not contain field"):
        backend.submit(empty_circuit(2), shots=10)


def test_result_valid_response(httpx_mock: HTTPXMock) -> None:
    """Check that AQTResource.result passes the authorization token
    and returns the raw response payload.
    """
    token = str(uuid.uuid4())
    backend = DummyResource(token)
    job_id = str(uuid.uuid4())

    payload = {
        "job": {
            "job_id": job_id,
            "job_type": "quantum_circuit",
            "label": "Example computation",
            "resource_id": backend._resource["id"],
            "workspace_id": backend._workspace,
        },
        "response": {"status": "cancelled"},
    }

    def handle_result(request: httpx.Request) -> httpx.Response:
        assert request.headers["sdk"] == "qiskit"
        assert request.headers["authorization"] == f"Bearer {token}"

        return httpx.Response(status_code=httpx.codes.OK, json=payload)

    httpx_mock.add_callback(handle_result, method="GET")

    response = backend.result(job_id)
    assert response == payload


def test_result_bad_request(httpx_mock: HTTPXMock) -> None:
    """Check that AQTResource.result raises an HTTPError if the request
    is flagged invalid by the server.
    """
    backend = DummyResource("")
    httpx_mock.add_response(status_code=httpx.codes.BAD_REQUEST)

    with pytest.raises(httpx.HTTPError):
        backend.result(str(uuid.uuid4()))


def test_resource_fixture_detect_invalid_circuits(
    offline_simulator_no_noise: MockSimulator,
) -> None:
    """Pass a circuit that cannot be converted to the AQT API to the mock simulator.
    This must fail.
    """
    qc = QuantumCircuit(2)
    qc.h(0)
    qc.cnot(0, 1)
    qc.measure_all()

    with pytest.raises(ValueError, match="^Circuit cannot be converted"):
        offline_simulator_no_noise.run(qc)
