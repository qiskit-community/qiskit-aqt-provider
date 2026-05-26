import json
from collections.abc import Callable
from uuid import uuid4

import pytest
from aqt_connector.models.circuits import Circuit
from aqt_connector.models.circuits import QuantumCircuit as AQTQuantumCircuit
from aqt_connector.models.operations import Measure, OperationModel
from httpx import Client, MockTransport, Request, Response

from qiskit_aqt_provider._direct.api_client import DirectAccessAPIClient
from qiskit_aqt_provider.api_client import models_direct as api_models_direct
from qiskit_aqt_provider.exceptions import AQTApiError, AQTRequestError


def test_fetch_available_qubits_returns_ion_count() -> None:
    """fetch_available_qubits() should return the num_ions value from the API response."""

    def handler(request: Request) -> Response:
        if request.url.path == "/status/ions":
            return Response(200, json={"num_ions": 7})
        return Response(404)

    client = _make_client(handler)
    assert client.fetch_available_qubits() == 7


def test_fetch_name_returns_resource_name() -> None:
    """fetch_name() should return the name string from the API response."""

    def handler(request: Request) -> Response:
        if request.url.path == "/system/name":
            return Response(200, json="my-device")
        return Response(404)

    client = _make_client(handler)
    assert client.fetch_name() == "my-device"


def test_submit_circuit_returns_job_id() -> None:
    """submit_circuit() should return the UUID from the API response."""
    job_id = uuid4()

    def handler(request: Request) -> Response:
        if request.url.path == "/circuit" and request.method == "PUT":
            return Response(200, json=str(job_id))
        return Response(404)

    client = _make_client(handler)
    returned_id = client.submit_circuit(_make_aqt_circuit())

    assert returned_id == job_id


def test_submit_circuit_sends_serialized_circuit_body() -> None:
    """submit_circuit() should PUT the circuit as a JSON body to /circuit."""
    received_bodies: list[bytes] = []

    def handler(request: Request) -> Response:
        if request.url.path == "/circuit" and request.method == "PUT":
            received_bodies.append(request.content)
            return Response(200, json=str(uuid4()))
        return Response(404)

    circuit = _make_aqt_circuit()
    _make_client(handler).submit_circuit(circuit)

    assert len(received_bodies) == 1
    assert json.loads(received_bodies[0]) == json.loads(circuit.model_dump_json())


def test_submit_circuit_raises_api_error_on_server_error() -> None:
    """submit_circuit() should raise AQTApiError when the server returns a 5xx response."""

    def handler(request: Request) -> Response:
        if request.url.path == "/circuit":
            return Response(500)
        return Response(404)

    with pytest.raises(AQTApiError):
        _make_client(handler).submit_circuit(_make_aqt_circuit())


def test_submit_circuit_raises_request_error_on_client_error() -> None:
    """submit_circuit() should raise AQTRequestError when the server returns a 4xx response."""

    def handler(request: Request) -> Response:
        if request.url.path == "/circuit":
            return Response(400)
        return Response(404)

    with pytest.raises(AQTRequestError):
        _make_client(handler).submit_circuit(_make_aqt_circuit())


def test_await_result_returns_finished_result() -> None:
    """await_result() should return a JobResultFinished payload when the job succeeded."""
    job_id = uuid4()
    api_result = api_models_direct.JobResult.create_finished(job_id=job_id, result=[[0, 1], [1, 0]])

    def handler(request: Request) -> Response:
        if request.url.path == f"/circuit/result/{job_id}":
            return Response(200, text=api_result.model_dump_json())
        return Response(404)

    result = _make_client(handler).await_result(job_id)

    assert isinstance(result.payload, api_models_direct.JobResultFinished)
    assert result.payload.result == [[0, 1], [1, 0]]


def test_await_result_returns_error_result() -> None:
    """await_result() should return a JobResultError payload when the job failed."""
    job_id = uuid4()
    api_result = api_models_direct.JobResult.create_error(job_id=job_id)

    def handler(request: Request) -> Response:
        if request.url.path == f"/circuit/result/{job_id}":
            return Response(200, text=api_result.model_dump_json())
        return Response(404)

    result = _make_client(handler).await_result(job_id)

    assert isinstance(result.payload, api_models_direct.JobResultError)


def test_await_result_uses_correct_job_id_in_path() -> None:
    """await_result() should request the result for the given job ID."""
    requested_paths: list[str] = []
    job_id = uuid4()
    api_result = api_models_direct.JobResult.create_finished(job_id=job_id, result=[[0]])

    def handler(request: Request) -> Response:
        requested_paths.append(request.url.path)
        return Response(200, text=api_result.model_dump_json())

    _make_client(handler).await_result(job_id)

    assert requested_paths == [f"/circuit/result/{job_id}"]


def _make_client(handler: Callable[[Request], Response]) -> DirectAccessAPIClient:
    http_client = Client(base_url="http://test.api", transport=MockTransport(handler))
    return DirectAccessAPIClient(http_client)


def _make_aqt_circuit() -> AQTQuantumCircuit:
    return AQTQuantumCircuit(
        number_of_qubits=1,
        repetitions=1,
        quantum_circuit=Circuit(root=[OperationModel(root=Measure())]),
    )
