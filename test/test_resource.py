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

import json
import math
import uuid
from contextlib import nullcontext
from typing import Any, ContextManager
from unittest import mock

import httpx
import pydantic as pdt
import pytest
import qiskit
from polyfactory.factories.pydantic_factory import ModelFactory
from pytest_httpx import HTTPXMock
from qiskit import QuantumCircuit
from qiskit.providers.exceptions import JobTimeoutError

from qiskit_aqt_provider import api_models
from qiskit_aqt_provider.aqt_job import AQTJob
from qiskit_aqt_provider.aqt_options import AQTOptions
from qiskit_aqt_provider.aqt_resource import AQTResource
from qiskit_aqt_provider.circuit_to_aqt import circuits_to_aqt_job
from qiskit_aqt_provider.test.circuits import assert_circuits_equal, empty_circuit, random_circuit
from qiskit_aqt_provider.test.fixtures import MockSimulator
from qiskit_aqt_provider.test.resources import DummyResource, TestResource
from qiskit_aqt_provider.versions import USER_AGENT


class OptionsFactory(ModelFactory[AQTOptions]):
    __model__ = AQTOptions

    query_timeout_seconds = 10.0


def test_options_set_query_timeout(offline_simulator_no_noise: AQTResource) -> None:
    """Set the query timeout for job status queries with different values."""
    backend = offline_simulator_no_noise

    # doesn't work with str
    with pytest.raises(pdt.ValidationError):
        backend.options.update_options(query_timeout_seconds="abc")

    # works with integers
    backend.options.update_options(query_timeout_seconds=123)
    assert backend.options.query_timeout_seconds == 123

    # works with floats
    backend.options.update_options(query_timeout_seconds=123.45)
    assert backend.options.query_timeout_seconds == 123.45

    # works with None (no timeout)
    backend.options.update_options(query_timeout_seconds=None)
    assert backend.options.query_timeout_seconds is None


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
    with pytest.raises(pdt.ValidationError):
        backend.options.update_options(query_period_seconds=None)

    # doesn't work with str
    with pytest.raises(pdt.ValidationError):
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
    qc.measure_all()

    job = backend.run(qiskit.transpile(qc, backend))

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

    job = backend.run(qiskit.transpile(qc, backend))

    with mock.patch.object(AQTJob, "status", wraps=job.status) as mocked_status:
        job.result()

    lower_bound = math.floor(response_delay / period_seconds)
    upper_bound = math.ceil(response_delay / period_seconds) + 1
    assert lower_bound <= mocked_status.call_count <= upper_bound


def test_run_options_propagation(offline_simulator_no_noise: MockSimulator) -> None:
    """Check that options passed to AQTResource.run are propagated to the corresponding job."""
    default = offline_simulator_no_noise.options.copy()

    while True:
        overrides = OptionsFactory.build()
        if overrides != default:
            break

    qc = QuantumCircuit(1)
    qc.measure_all()

    # don't submit the circuit to the simulator
    with mock.patch.object(AQTJob, "submit") as mocked_submit:
        job = offline_simulator_no_noise.run(qc, **overrides.dict())
        assert job.options == overrides

    mocked_submit.assert_called_once()


def test_run_options_unknown(offline_simulator_no_noise: MockSimulator) -> None:
    """Check that AQTResource.run accepts but warns about unknown options."""
    default = offline_simulator_no_noise.options.copy()
    overrides = {"shots": 123, "unknown_option": True}
    assert set(overrides) - set(default) == {"unknown_option"}

    qc = QuantumCircuit(1)
    qc.measure_all()

    with mock.patch.object(AQTJob, "submit") as mocked_submit:
        with pytest.warns(UserWarning, match="not used"):
            job = offline_simulator_no_noise.run(qc, **overrides)

        assert job.options.shots == 123

    mocked_submit.assert_called_once()


def test_run_options_invalid(offline_simulator_no_noise: MockSimulator) -> None:
    """Check that AQTResource.run reject valid option names with invalid values."""
    qc = QuantumCircuit(1)
    qc.measure_all()

    with pytest.raises(pdt.ValidationError, match="shots"):
        offline_simulator_no_noise.run(qc, shots=-123)


def test_double_job_submission(offline_simulator_no_noise: MockSimulator) -> None:
    """Check that attempting to re-submit a job raises a RuntimeError."""
    qc = QuantumCircuit(1)
    qc.r(3.14, 0.0, 0)
    qc.measure_all()

    # AQTResource.run submits the job
    job = offline_simulator_no_noise.run(qc)

    with pytest.raises(RuntimeError, match=f"{job.job_id()}"):
        job.submit()

    # Check that the job was actually submitted
    ((submitted_circuit,),) = offline_simulator_no_noise.submitted_circuits
    assert_circuits_equal(submitted_circuit, qc)


def test_offline_simulator_invalid_job_id(offline_simulator_no_noise: MockSimulator) -> None:
    """Check that the offline simulator raises UnknownJobError if the job id passed
    to `result()` is invalid.
    """
    qc = QuantumCircuit(1)
    qc.measure_all()

    job = offline_simulator_no_noise.run([qc], shots=1)
    job_id = uuid.UUID(hex=job.job_id())
    invalid_job_id = uuid.uuid4()
    assert invalid_job_id != job_id

    with pytest.raises(api_models.UnknownJobError, match=str(invalid_job_id)):
        offline_simulator_no_noise.result(invalid_job_id)

    # querying the actual job is successful
    result = offline_simulator_no_noise.result(job_id)
    assert result.job.job_id == job_id


def test_submit_valid_response(httpx_mock: HTTPXMock) -> None:
    """Check that AQTResource.submit passes the authorization token and
    extracts the correct job_id when the response payload is valid.
    """
    token = str(uuid.uuid4())
    backend = DummyResource(token)
    expected_job_id = uuid.uuid4()

    def handle_submit(request: httpx.Request) -> httpx.Response:
        assert request.headers["user-agent"] == USER_AGENT
        assert request.headers["authorization"] == f"Bearer {token}"

        return httpx.Response(
            status_code=httpx.codes.OK,
            json=json.loads(
                api_models.Response.queued(
                    job_id=expected_job_id,
                    resource_id=backend.resource_id.resource_id,
                    workspace_id=backend.resource_id.workspace_id,
                ).json()
            ),
        )

    httpx_mock.add_callback(handle_submit, method="POST")

    job = AQTJob(backend, circuits=[empty_circuit(2)], options=AQTOptions(shots=10))
    job.submit()
    assert job.job_id() == str(expected_job_id)


def test_submit_payload_matches(httpx_mock: HTTPXMock) -> None:
    """Check that the quantum circuits jobs payload is correctly submitted to the API endpoint."""
    backend = DummyResource("")
    shots = 123
    qc = qiskit.transpile(random_circuit(2), backend)
    expected_job_payload = circuits_to_aqt_job([qc], shots=shots)
    expected_job_id = uuid.uuid4()

    def handle_submit(request: httpx.Request) -> httpx.Response:
        assert request.headers["user-agent"] == USER_AGENT
        assert request.url.path.endswith(
            f"submit/{backend.resource_id.workspace_id}/{backend.resource_id.resource_id}"
        )

        data = api_models.JobSubmission.parse_raw(request.content.decode("utf-8"))
        assert data == expected_job_payload

        return httpx.Response(
            status_code=httpx.codes.OK,
            json=json.loads(
                api_models.Response.queued(
                    job_id=expected_job_id,
                    resource_id=backend.resource_id.resource_id,
                    workspace_id=backend.resource_id.workspace_id,
                ).json()
            ),
        )

    httpx_mock.add_callback(handle_submit, method="POST")

    qc = qiskit.transpile(random_circuit(2), backend)
    job = AQTJob(backend, circuits=[qc], options=AQTOptions(shots=shots))
    job.submit()
    assert job.job_id() == str(expected_job_id)


def test_submit_bad_request(httpx_mock: HTTPXMock) -> None:
    """Check that AQTResource.submit raises an HTTPError if the request
    is flagged invalid by the server.
    """
    backend = DummyResource("")
    httpx_mock.add_response(status_code=httpx.codes.BAD_REQUEST)

    job = AQTJob(backend, circuits=[empty_circuit(2)], options=AQTOptions(shots=10))
    with pytest.raises(httpx.HTTPError):
        job.submit()


def test_result_valid_response(httpx_mock: HTTPXMock) -> None:
    """Check that AQTResource.result passes the authorization token
    and returns the raw response payload.
    """
    token = str(uuid.uuid4())
    backend = DummyResource(token)
    job_id = uuid.uuid4()

    payload = api_models.Response.cancelled(
        job_id=job_id,
        resource_id=backend.resource_id.resource_id,
        workspace_id=backend.resource_id.workspace_id,
    )

    def handle_result(request: httpx.Request) -> httpx.Response:
        assert request.headers["user-agent"] == USER_AGENT
        assert request.headers["authorization"] == f"Bearer {token}"
        assert request.url.path.endswith(f"result/{job_id}")

        return httpx.Response(status_code=httpx.codes.OK, json=json.loads(payload.json()))

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
        backend.result(uuid.uuid4())


def test_result_unknown_job(httpx_mock: HTTPXMock) -> None:
    """Check that AQTResource.result raises UnknownJobError if the API
    responds with an UnknownJob payload.
    """
    backend = DummyResource("")
    job_id = uuid.uuid4()

    httpx_mock.add_response(json=json.loads(api_models.Response.unknown_job(job_id=job_id).json()))

    with pytest.raises(api_models.UnknownJobError, match=str(job_id)):
        backend.result(job_id)


def test_offline_simulator_detects_invalid_circuits(
    offline_simulator_no_noise: MockSimulator,
) -> None:
    """Pass a circuit that cannot be converted to the AQT API to the offline simulator.
    This must fail.
    """
    qc = QuantumCircuit(2)
    qc.h(0)
    qc.cx(0, 1)
    qc.measure_all()

    with pytest.raises(ValueError, match="^Operation 'h' not in basis gate set"):
        offline_simulator_no_noise.run(qc)


def test_offline_simulator_propagate_shots_option(
    offline_simulator_no_noise: MockSimulator,
) -> None:
    """Check various ways of configuring the number of repetitions."""
    qc = qiskit.transpile(random_circuit(2), offline_simulator_no_noise)

    default_shots = sum(offline_simulator_no_noise.run(qc).result().get_counts().values())
    assert default_shots == AQTOptions().shots

    # TODO: use annotated-types to get unified access to upper bound
    shots = min(default_shots + 40, AQTOptions.__fields__["shots"].field_info.le)
    assert shots != default_shots

    # configure shots in AQTResource.run
    shots_run = sum(offline_simulator_no_noise.run(qc, shots=shots).result().get_counts().values())
    assert shots_run == shots

    # configure shots in qiskit.execute
    shots_execute = sum(
        qiskit.execute(qc, offline_simulator_no_noise, shots=shots).result().get_counts().values()
    )
    assert shots_execute == shots

    # configure shots in resource options
    offline_simulator_no_noise.options.shots = shots
    shots_options = sum(offline_simulator_no_noise.run(qc).result().get_counts().values())
    assert shots_options == shots

    # qiskit.execute overrides resource options
    shots_override = min(shots + 40, AQTOptions.__fields__["shots"].field_info.le)
    assert shots_override != shots
    assert shots_override != default_shots
    assert offline_simulator_no_noise.options.shots != shots_override
    shots = sum(
        qiskit.execute(qc, offline_simulator_no_noise, shots=shots_override)
        .result()
        .get_counts()
        .values()
    )
    assert shots == shots_override


@pytest.mark.parametrize(
    ("memory", "context"),
    [(True, nullcontext()), (False, pytest.raises(qiskit.QiskitError, match="No memory"))],
)
def test_offline_simulator_run_propagate_memory_option(
    memory: bool,
    context: ContextManager[Any],
    offline_simulator_no_noise: MockSimulator,
) -> None:
    """Check that the memory option can be set on `AQTResource.run`."""
    qc = qiskit.transpile(random_circuit(2), offline_simulator_no_noise)
    default_shots = AQTOptions().shots

    result = offline_simulator_no_noise.run(qc, memory=memory).result()
    with context:
        assert len(result.get_memory()) == default_shots


@pytest.mark.parametrize(
    ("memory", "context"),
    [(True, nullcontext()), (False, pytest.raises(qiskit.QiskitError, match="No memory"))],
)
def test_offline_simulator_execute_propagate_memory_option(
    memory: bool, context: ContextManager[Any], offline_simulator_no_noise: MockSimulator
) -> None:
    """Check that the memory option can be set in `qiskit.execute`."""
    qc = random_circuit(2)
    default_shots = AQTOptions().shots

    result = qiskit.execute(qc, offline_simulator_no_noise, memory=memory).result()
    with context:
        assert len(result.get_memory()) == default_shots


@pytest.mark.parametrize(
    ("memory", "context"),
    [(True, nullcontext()), (False, pytest.raises(qiskit.QiskitError, match="No memory"))],
)
def test_offline_simulator_resource_propagate_memory_option(
    memory: bool, context: ContextManager[Any], offline_simulator_no_noise: MockSimulator
) -> None:
    """Check that the memory option can be set as resource option."""
    qc = qiskit.transpile(random_circuit(2), offline_simulator_no_noise)
    default_shots = AQTOptions().shots

    offline_simulator_no_noise.options.memory = memory
    result = offline_simulator_no_noise.run(qc).result()
    with context:
        assert len(result.get_memory()) == default_shots


@pytest.mark.parametrize(
    ("memory", "context"),
    [(True, nullcontext()), (False, pytest.raises(qiskit.QiskitError, match="No memory"))],
)
def test_offline_simulator_execute_override_memory_option(
    memory: bool, context: ContextManager[Any], offline_simulator_no_noise: MockSimulator
) -> None:
    """Check that setting `memory` through `qiskit.execute` overrides the resource options."""
    qc = random_circuit(2)
    default_shots = AQTOptions().shots

    offline_simulator_no_noise.options.memory = not memory
    result = qiskit.execute(qc, offline_simulator_no_noise, memory=memory).result()
    with context:
        assert len(result.get_memory()) == default_shots
