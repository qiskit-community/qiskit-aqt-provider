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

import itertools
import json
import math
import re
import uuid
from contextlib import AbstractContextManager, nullcontext
from typing import Any
from unittest import mock

import httpx
import pydantic as pdt
import pytest
import qiskit
from polyfactory.factories.pydantic_factory import ModelFactory
from pytest_httpx import HTTPXMock
from qiskit import QuantumCircuit
from qiskit.providers import JobStatus
from qiskit.providers.exceptions import JobTimeoutError
from typing_extensions import assert_type

from qiskit_aqt_provider.api_client import models as api_models
from qiskit_aqt_provider.api_client import models_direct as api_models_direct
from qiskit_aqt_provider.api_client.errors import APIError
from qiskit_aqt_provider.aqt_job import AQTJob
from qiskit_aqt_provider.aqt_options import AQTDirectAccessOptions, AQTOptions
from qiskit_aqt_provider.aqt_resource import AQTResource
from qiskit_aqt_provider.circuit_to_aqt import circuits_to_aqt_job
from qiskit_aqt_provider.test.circuits import assert_circuits_equal, empty_circuit, random_circuit
from qiskit_aqt_provider.test.fixtures import MockSimulator
from qiskit_aqt_provider.test.resources import (
    DummyDirectAccessResource,
    DummyResource,
    TestResource,
)
from qiskit_aqt_provider.versions import USER_AGENT_EXTRA


class OptionsFactory(ModelFactory[AQTOptions]):
    """Factory of random but well-formed options data."""

    __model__ = AQTOptions

    query_timeout_seconds = 10.0


def test_basis_gates_legacy_config_and_transpiler_match(
    offline_simulator_no_noise: AQTResource,
) -> None:
    """Check that the basis gates sets are consistent.

    The backend advertises the basis gate set in the legacy backend configuration namespace
    and the transpiler target. Check that these two match.

    Also check that the basis gate set and the gates constraints in the legacy configuration
    namespace are consistent.
    """
    legacy_config = offline_simulator_no_noise.configuration()
    legacy_basis_gates = set(legacy_config.basis_gates)
    legacy_gates = {entry.name for entry in legacy_config.gates}

    target_operations = set(offline_simulator_no_noise.target.operation_names)

    # The transpilation target also advertises the 'measure' operation, which is not a gate.
    assert target_operations - legacy_basis_gates == {"measure"}
    assert legacy_basis_gates == legacy_gates


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


def test_options_types_and_constraints_cloud_resource(
    offline_simulator_no_noise: AQTResource,
) -> None:
    """Check that the options models and constraints are as expected for cloud backends."""
    assert_type(offline_simulator_no_noise.options, AQTOptions)
    assert isinstance(offline_simulator_no_noise.options, AQTOptions)
    assert offline_simulator_no_noise.options.max_shots() == 2000

    # Check that the default options in Qiskit format match the Pydantic model.
    assert offline_simulator_no_noise.options.model_dump() == {
        **offline_simulator_no_noise.__class__._default_options()
    }


def test_options_types_and_constraints_direct_access_resource() -> None:
    """Check that the options models and constraints are as expected for direct-access backends."""
    backend = DummyDirectAccessResource("token")

    assert_type(backend.options, AQTDirectAccessOptions)
    assert isinstance(backend.options, AQTDirectAccessOptions)
    assert backend.options.max_shots() == 200

    # Check that the default options in Qiskit format match the Pydantic model.
    assert backend.options.model_dump() == {**backend.__class__._default_options()}


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
    default = offline_simulator_no_noise.options.model_copy()

    while True:
        overrides = OptionsFactory.build()
        if overrides != default:
            break

    qc = QuantumCircuit(1)
    qc.measure_all()

    # don't submit the circuit to the simulator
    with mock.patch.object(AQTJob, "submit") as mocked_submit:
        job = offline_simulator_no_noise.run(qc, **overrides.model_dump())
        assert job.options == overrides

    mocked_submit.assert_called_once()


def test_run_options_unknown(offline_simulator_no_noise: MockSimulator) -> None:
    """Check that AQTResource.run accepts but warns about unknown options."""
    default = offline_simulator_no_noise.options.model_copy()
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
        assert USER_AGENT_EXTRA in request.headers["user-agent"]
        assert request.headers["authorization"] == f"Bearer {token}"

        return httpx.Response(
            status_code=httpx.codes.OK,
            json=json.loads(
                api_models.Response.queued(
                    job_id=expected_job_id,
                    resource_id=backend.resource_id.resource_id,
                    workspace_id=backend.resource_id.workspace_id,
                ).model_dump_json()
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
        assert USER_AGENT_EXTRA in request.headers["user-agent"]
        assert request.url.path.endswith(
            f"submit/{backend.resource_id.workspace_id}/{backend.resource_id.resource_id}"
        )

        data = api_models.SubmitJobRequest.model_validate_json(request.content.decode("utf-8"))
        assert data == expected_job_payload

        return httpx.Response(
            status_code=httpx.codes.OK,
            json=json.loads(
                api_models.Response.queued(
                    job_id=expected_job_id,
                    resource_id=backend.resource_id.resource_id,
                    workspace_id=backend.resource_id.workspace_id,
                ).model_dump_json()
            ),
        )

    httpx_mock.add_callback(handle_submit, method="POST")

    qc = qiskit.transpile(random_circuit(2), backend)
    job = AQTJob(backend, circuits=[qc], options=AQTOptions(shots=shots))
    job.submit()
    assert job.job_id() == str(expected_job_id)


def test_submit_bad_request(httpx_mock: HTTPXMock) -> None:
    """Check that AQTResource.submit raises an APIError if the request
    is flagged invalid by the server.
    """
    backend = DummyResource("")
    httpx_mock.add_response(status_code=httpx.codes.BAD_REQUEST)

    job = AQTJob(backend, circuits=[empty_circuit(2)], options=AQTOptions(shots=10))
    with pytest.raises(APIError) as excinfo:
        job.submit()

    status_error = excinfo.value.__cause__
    assert isinstance(status_error, httpx.HTTPStatusError)
    assert status_error.response.status_code == httpx.codes.BAD_REQUEST


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
        assert USER_AGENT_EXTRA in request.headers["user-agent"]
        assert request.headers["authorization"] == f"Bearer {token}"
        assert request.url.path.endswith(f"result/{job_id}")

        return httpx.Response(
            status_code=httpx.codes.OK, json=json.loads(payload.model_dump_json())
        )

    httpx_mock.add_callback(handle_result, method="GET")

    response = backend.result(job_id)
    assert response == payload


def test_result_bad_request(httpx_mock: HTTPXMock) -> None:
    """Check that AQTResource.result raises an APIError if the request
    is flagged invalid by the server.
    """
    backend = DummyResource("")
    httpx_mock.add_response(status_code=httpx.codes.BAD_REQUEST)

    with pytest.raises(APIError) as excinfo:
        backend.result(uuid.uuid4())

    status_error = excinfo.value.__cause__
    assert isinstance(status_error, httpx.HTTPStatusError)
    assert status_error.response.status_code == httpx.codes.BAD_REQUEST


def test_result_unknown_job(httpx_mock: HTTPXMock) -> None:
    """Check that AQTResource.result raises UnknownJobError if the API
    responds with an UnknownJob payload.
    """
    backend = DummyResource("")
    job_id = uuid.uuid4()

    httpx_mock.add_response(
        json=json.loads(api_models.Response.unknown_job(job_id=job_id).model_dump_json())
    )

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

    shots = min(default_shots + 40, AQTOptions.max_shots())
    assert shots != default_shots

    # configure shots in AQTResource.run
    shots_run = sum(offline_simulator_no_noise.run(qc, shots=shots).result().get_counts().values())
    assert shots_run == shots

    # configure shots in resource options
    offline_simulator_no_noise.options.shots = shots
    shots_options = sum(offline_simulator_no_noise.run(qc).result().get_counts().values())
    assert shots_options == shots


@pytest.mark.parametrize(
    ("memory", "context"),
    [(True, nullcontext()), (False, pytest.raises(qiskit.QiskitError, match="No memory"))],
)
def test_offline_simulator_run_propagate_memory_option(
    memory: bool,
    context: AbstractContextManager[Any],
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
def test_offline_simulator_resource_propagate_memory_option(
    memory: bool, context: AbstractContextManager[Any], offline_simulator_no_noise: MockSimulator
) -> None:
    """Check that the memory option can be set as resource option."""
    qc = qiskit.transpile(random_circuit(2), offline_simulator_no_noise)
    default_shots = AQTOptions().shots

    offline_simulator_no_noise.options.memory = memory
    result = offline_simulator_no_noise.run(qc).result()
    with context:
        assert len(result.get_memory()) == default_shots


def test_direct_access_bad_request(httpx_mock: HTTPXMock) -> None:
    """Check that direct-access resources raise an APIError on bad requests."""
    backend = DummyDirectAccessResource("token")
    httpx_mock.add_response(status_code=httpx.codes.BAD_REQUEST)

    job = backend.run(empty_circuit(2))
    with pytest.raises(APIError) as excinfo:
        job.result()

    status_error = excinfo.value.__cause__
    assert isinstance(status_error, httpx.HTTPStatusError)
    assert status_error.response.status_code == httpx.codes.BAD_REQUEST


def test_direct_access_too_few_ions_error_message(httpx_mock: HTTPXMock) -> None:
    """Check error reporting when requesting more qubits than loaded ions."""
    backend = DummyDirectAccessResource("token")
    detail_str = "requested qubits > available qubits"
    httpx_mock.add_response(
        status_code=httpx.codes.REQUEST_ENTITY_TOO_LARGE, json={"detail": detail_str}
    )

    job = backend.run(empty_circuit(2))
    with pytest.raises(APIError, match=detail_str) as excinfo:
        job.result()

    # The exception chain contains the original HTTP status error
    status_error = excinfo.value.__cause__
    assert isinstance(status_error, httpx.HTTPStatusError)
    assert status_error.response.status_code == httpx.codes.REQUEST_ENTITY_TOO_LARGE


@pytest.mark.parametrize("success", [False, True])
def test_direct_access_job_status(success: bool, httpx_mock: HTTPXMock) -> None:
    """Check the expected Qiskit job status on direct-access resources.

    Since the transactions are synchronous, there are only three possible statuses:
    1. initializing: the job was created but is not executing
    2. done: the job executed successfully
    3. error: the job execution failed.
    """
    shots = 100

    def handle_submit(request: httpx.Request) -> httpx.Response:
        assert USER_AGENT_EXTRA in request.headers["user-agent"]

        return httpx.Response(status_code=httpx.codes.OK, text=f'"{uuid.uuid4()}"')

    def handle_result(request: httpx.Request) -> httpx.Response:
        assert USER_AGENT_EXTRA in request.headers["user-agent"]

        _, job_id = request.url.path.rsplit("/", maxsplit=1)

        return httpx.Response(
            status_code=httpx.codes.OK,
            json=json.loads(
                api_models_direct.JobResult.create_finished(
                    job_id=uuid.UUID(job_id), result=[[0] for _ in range(shots)]
                ).model_dump_json()
                if success
                else api_models_direct.JobResult.create_error(
                    job_id=uuid.UUID(job_id)
                ).model_dump_json()
            ),
        )

    httpx_mock.add_callback(handle_submit, method="PUT", url=re.compile(".+/circuit/?$"))
    httpx_mock.add_callback(
        handle_result, method="GET", url=re.compile(".+/circuit/result/[0-9a-f-]+$")
    )

    backend = DummyDirectAccessResource("token")
    job = backend.run(empty_circuit(1), shots=shots)

    assert job.status() is JobStatus.INITIALIZING

    result = job.result()
    assert result.success is success

    if success:
        assert job.status() is JobStatus.DONE
    else:
        assert job.status() is JobStatus.ERROR


@pytest.mark.parametrize("token", [str(uuid.uuid4()), ""])
def test_direct_access_mocked_successful_transaction(token: str, httpx_mock: HTTPXMock) -> None:
    """Mock a successful single-circuit transaction on a direct-access resource."""
    backend = DummyDirectAccessResource(token)
    backend.options.with_progress_bar = False

    shots = 122
    qc = empty_circuit(2)

    expected_job_id = str(uuid.uuid4())

    def assert_valid_token(headers: httpx.Headers) -> None:
        if token:
            assert headers["authorization"] == f"Bearer {token}"
        else:
            assert "authorization" not in headers

    def handle_submit(request: httpx.Request) -> httpx.Response:
        assert USER_AGENT_EXTRA in request.headers["user-agent"]
        assert_valid_token(request.headers)

        data = api_models.QuantumCircuit.model_validate_json(request.content.decode("utf-8"))
        assert data.repetitions == shots

        return httpx.Response(
            status_code=httpx.codes.OK,
            text=f'"{expected_job_id}"',
        )

    def handle_result(request: httpx.Request) -> httpx.Response:
        assert USER_AGENT_EXTRA in request.headers["user-agent"]
        assert_valid_token(request.headers)

        _, job_id = request.url.path.rsplit("/", maxsplit=1)
        assert job_id == expected_job_id

        return httpx.Response(
            status_code=httpx.codes.OK,
            json=json.loads(
                api_models_direct.JobResult.create_finished(
                    job_id=uuid.UUID(job_id),
                    result=[[0, 0] if s % 2 == 0 else [1, 0] for s in range(shots)],
                ).model_dump_json()
            ),
        )

    httpx_mock.add_callback(handle_submit, method="PUT", url=re.compile(".+/circuit/?$"))
    httpx_mock.add_callback(
        handle_result, method="GET", url=re.compile(".+/circuit/result/[0-9a-f-]+$")
    )

    job = backend.run(qc, shots=shots)
    result = job.result()

    assert result.get_counts() == {"00": shots // 2, "01": shots // 2}


@pytest.mark.httpx_mock(can_send_already_matched_responses=True)
def test_direct_access_mocked_failed_transaction(httpx_mock: HTTPXMock) -> None:
    """Mock a failed multi-circuit transaction on a direct-access resource.

    The first two circuits succeed, the third one not. The fourth circuit would succeed,
    but is never executed.
    """
    token = str(uuid.uuid4())
    backend = DummyDirectAccessResource(token)
    backend.options.with_progress_bar = False

    shots = 122
    qc = empty_circuit(2)

    job_ids = [str(uuid.uuid4()) for _ in range(4)]
    # produce 2 times the same id before going to the next, one value
    # for handle_submit, the other one for handle result.
    job_ids_iter = itertools.chain.from_iterable(zip(job_ids, job_ids))

    # circuit executions' planned success
    success = [True, True, False, True]
    success_iter = iter(success)

    circuit_submissions = 0

    def handle_submit(request: httpx.Request) -> httpx.Response:
        assert USER_AGENT_EXTRA in request.headers["user-agent"]

        data = api_models.QuantumCircuit.model_validate_json(request.content.decode("utf-8"))
        assert data.repetitions == shots

        nonlocal circuit_submissions
        circuit_submissions += 1

        return httpx.Response(
            status_code=httpx.codes.OK,
            text=f'"{next(job_ids_iter)}"',
        )

    def handle_result(request: httpx.Request) -> httpx.Response:
        assert USER_AGENT_EXTRA in request.headers["user-agent"]

        _, job_id = request.url.path.rsplit("/", maxsplit=1)
        assert job_id == next(job_ids_iter)

        return httpx.Response(
            status_code=httpx.codes.OK,
            json=json.loads(
                api_models_direct.JobResult.create_finished(
                    job_id=uuid.UUID(job_id), result=[[0, 1] for _ in range(shots)]
                ).model_dump_json()
                if next(success_iter)
                else api_models_direct.JobResult.create_error(
                    job_id=uuid.UUID(job_id)
                ).model_dump_json()
            ),
        )

    httpx_mock.add_callback(handle_submit, method="PUT", url=re.compile(".+/circuit/?$"))
    httpx_mock.add_callback(
        handle_result, method="GET", url=re.compile(".+/circuit/result/[0-9a-f-]+$")
    )

    job = backend.run([qc, qc, qc, qc], shots=shots)
    result = job.result()

    assert not result.success  # not all circuits executed successfully

    counts = result.get_counts()
    assert isinstance(counts, list)  # multiple successful circuit executions
    assert len(counts) == 2  # the first two circuits executed successfully
    assert counts == [{"10": shots}, {"10": shots}]

    assert circuit_submissions == 3  # the last circuit was never submitted
