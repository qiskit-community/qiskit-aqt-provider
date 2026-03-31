from pathlib import Path
from uuid import UUID

import pytest
from aqt_connector import ArnicaConfig
from aqt_connector.models.arnica.request_bodies.jobs import SubmitJobRequest
from aqt_connector.models.operations import Measure
from qiskit import QuantumCircuit

from test.acceptance import dsl
from test.acceptance.conftest import DummyArnicaServer


def test_submits_native_circuit_to_cloud_backend(
    monkeypatch: pytest.MonkeyPatch, dummy_server: DummyArnicaServer, tmp_path: Path
) -> None:
    """It should submit a native circuit to a cloud backend."""
    dsl.user.has_cloud_access(monkeypatch, "arnica_token")
    cloud_provider_config = ArnicaConfig(tmp_path)
    cloud_provider_config.arnica_url = dummy_server.base_url

    circuit = QuantumCircuit(2)
    circuit.measure_all()
    dsl.user.submits_circuit(cloud_provider_config, workspace_id="w1", backend_id="r1", circuit=circuit)

    requests = dummy_server.get_recorded_requests()
    submitted_job = SubmitJobRequest.model_validate(requests[-1]["body"])
    assert len(submitted_job.payload.circuits) == 1
    assert len(submitted_job.payload.circuits[0].quantum_circuit.root) == 1
    assert isinstance(submitted_job.payload.circuits[0].quantum_circuit.root[0].root, Measure)


def test_submitted_job_has_stable_identity(
    monkeypatch: pytest.MonkeyPatch, dummy_server: DummyArnicaServer, tmp_path: Path
) -> None:
    """A job should have a stable identity after submission."""
    dsl.user.has_cloud_access(monkeypatch, "arnica_token")
    cloud_provider_config = ArnicaConfig(tmp_path)
    cloud_provider_config.arnica_url = dummy_server.base_url

    circuit = QuantumCircuit(2)
    circuit.measure_all()
    job = dsl.user.submits_circuit(cloud_provider_config, workspace_id="w1", backend_id="r1", circuit=circuit)

    assert job.job_id() == "c8919003-1bc1-445f-a968-e7f4c90029d3"


def test_submission_uses_correct_workspace_and_resource(
    monkeypatch: pytest.MonkeyPatch, dummy_server: DummyArnicaServer, tmp_path: Path
) -> None:
    """It should use the correct workspace and resource for submission."""
    dsl.user.has_cloud_access(monkeypatch, "arnica_token")
    cloud_provider_config = ArnicaConfig(tmp_path)
    cloud_provider_config.arnica_url = dummy_server.base_url

    circuit = QuantumCircuit(2)
    circuit.measure_all()
    dsl.user.submits_circuit(cloud_provider_config, workspace_id="w1", backend_id="r1", circuit=circuit)

    requests = dummy_server.get_recorded_requests()
    assert requests[-1]["path"] == "/v1/submit/w1/r1"


def test_submission_forwards_supported_runtime_options(
    monkeypatch: pytest.MonkeyPatch, dummy_server: DummyArnicaServer, tmp_path: Path
) -> None:
    """It should forward supported runtime options in the submission."""
    dsl.user.has_cloud_access(monkeypatch, "arnica_token")
    cloud_provider_config = ArnicaConfig(tmp_path)
    cloud_provider_config.arnica_url = dummy_server.base_url

    circuit = QuantumCircuit(2)
    circuit.measure_all()
    dsl.user.submits_circuit(cloud_provider_config, workspace_id="w1", backend_id="r1", circuit=circuit, shots=73)

    requests = dummy_server.get_recorded_requests()
    submitted_job = SubmitJobRequest.model_validate(requests[-1]["body"])
    assert submitted_job.payload.circuits[0].repetitions == 73


def test_submission_failure_is_surfaced_clearly(
    monkeypatch: pytest.MonkeyPatch, dummy_server: DummyArnicaServer, tmp_path: Path
) -> None:
    """If submission fails, the failure should be surfaced clearly."""
    dsl.user.has_cloud_access(monkeypatch, "arnica_token")
    cloud_provider_config = ArnicaConfig(tmp_path)
    cloud_provider_config.arnica_url = dummy_server.base_url

    with dsl.expect.job_submission_fails_with_message("Workspace not available."):
        circuit = QuantumCircuit(2)
        circuit.measure_all()
        dsl.user.submits_circuit(cloud_provider_config, workspace_id="w93", backend_id="r1", circuit=circuit)
