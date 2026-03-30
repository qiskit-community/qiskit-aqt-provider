import json
import re
import uuid
from datetime import datetime
from typing import Optional

import pytest
from aqt_connector import ArnicaApp
from aqt_connector.models.arnica.jobs import BasicJobMetadata
from aqt_connector.models.arnica.resources import ResourceStatus, ResourceType
from aqt_connector.models.arnica.response_bodies.jobs import SubmitJobResponse
from aqt_connector.models.arnica.response_bodies.resources import ResourceDetails
from httpx import Client, MockTransport, Request, Response
from qiskit import QuantumCircuit

from qiskit_aqt_provider._cloud.job import CloudJob
from qiskit_aqt_provider._cloud.resource import CloudResource
from qiskit_aqt_provider.api_client.errors import APIError

_JOB_ID = uuid.UUID("12345678-1234-5678-1234-567812345678")

_RESOURCE_DETAILS = ResourceDetails(
    id="r1",
    name="R1",
    type=ResourceType.DEVICE,
    status=ResourceStatus.ONLINE,
    available_qubits=20,
    status_updated_at=datetime(2026, 3, 27, 0, 0, 0),
)


def _make_resource(handler: MockTransport) -> CloudResource:
    client = Client(base_url="https://arnica.aqt.eu/api", transport=handler)
    arnica = ArnicaApp()
    return CloudResource(arnica, client, "w1", _RESOURCE_DETAILS)


def _ok_handler(_: Request) -> Response:
    return Response(
        status_code=200,
        text=SubmitJobResponse(
            job=BasicJobMetadata(job_id=_JOB_ID, resource_id="r1", workspace_id="w1")
        ).model_dump_json(),
    )


def _single_qubit_circuit() -> QuantumCircuit:
    """A minimal valid circuit (measure-only) that passes circuits_to_aqt_job."""
    qc = QuantumCircuit(1)
    qc.measure_all()
    return qc


def test_run_single_circuit_returns_cloud_job() -> None:
    """It returns a CloudJob for a single QuantumCircuit."""
    resource = _make_resource(MockTransport(_ok_handler))

    job = resource.run(_single_qubit_circuit())

    assert isinstance(job, CloudJob)


def test_run_list_of_circuits_returns_cloud_job() -> None:
    """It returns a CloudJob for a list of QuantumCircuits."""
    resource = _make_resource(MockTransport(_ok_handler))

    job = resource.run([_single_qubit_circuit(), _single_qubit_circuit()])

    assert isinstance(job, CloudJob)


def test_run_returns_job_id_from_response() -> None:
    """It returns a CloudJob whose job_id matches the server response."""
    resource = _make_resource(MockTransport(_ok_handler))

    job = resource.run(_single_qubit_circuit())

    assert job.job_id() == str(_JOB_ID)


def test_run_posts_to_correct_url() -> None:
    """It submits a POST request to /v1/submit/{workspace_id}/{resource_id}."""
    captured: list[Request] = []

    def capturing_handler(request: Request) -> Response:
        captured.append(request)
        return _ok_handler(request)

    resource = _make_resource(MockTransport(capturing_handler))
    resource.run(_single_qubit_circuit())

    assert len(captured) == 1
    assert captured[0].url.path == "/api/v1/submit/w1/r1"


@pytest.mark.parametrize(
    ("shots_arg", "expected_shots"),
    [
        (None, 100),  # default shots used when shots_arg is None
        (42, 42),  # shots_arg overrides default shots
    ],
    ids=["default shots", "custom shots"],
)
def test_run_sets_correct_shot_count(shots_arg: Optional[int], expected_shots: int) -> None:
    """It sets the correct shot count based on the provided argument or default."""
    captured: list[Request] = []

    def capturing_handler(request: Request) -> Response:
        captured.append(request)
        return _ok_handler(request)

    resource = _make_resource(MockTransport(capturing_handler))
    resource.run(_single_qubit_circuit(), shots=shots_arg)

    body = captured[0].read()
    payload = json.loads(body)
    assert payload["payload"]["circuits"][0]["repetitions"] == expected_shots


def test_run_raises_for_shots_below_minimum() -> None:
    """It raises ValueError when shots is less than 1."""
    resource = _make_resource(MockTransport(lambda _: Response(404)))

    with pytest.raises(ValueError, match=re.escape("Shots must be in the range [1, 2000].")):
        resource.run(_single_qubit_circuit(), shots=0)


def test_run_raises_for_shots_above_maximum() -> None:
    """It raises ValueError when shots exceeds MAX_SHOTS (2000)."""
    resource = _make_resource(MockTransport(lambda _: Response(404)))

    with pytest.raises(ValueError, match=re.escape("Shots must be in the range [1, 2000].")):
        resource.run(_single_qubit_circuit(), shots=CloudResource.MAX_SHOTS + 1)


def test_run_raises_api_error_on_http_error_response() -> None:
    """It raises APIError when the server returns a non-2xx status."""
    resource = _make_resource(MockTransport(lambda _: Response(500, json={"detail": "internal error"})))

    with pytest.raises(APIError):
        resource.run(_single_qubit_circuit())
