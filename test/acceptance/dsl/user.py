from typing import Optional, Union

import pytest
from aqt_connector import ArnicaConfig
from qiskit import QuantumCircuit

from qiskit_aqt_provider._cloud.job import CloudJob
from qiskit_aqt_provider._cloud.resource import CloudResource
from qiskit_aqt_provider.aqt_provider import AQTProvider


def has_cloud_access(monkeypatch: pytest.MonkeyPatch, token: str) -> None:
    """The user has access to the cloud provider with the given token.

    Args:
        monkeypatch (pytest.MonkeyPatch): The pytest monkeypatch fixture.
        token (str): The token to use for cloud access.
    """
    monkeypatch.setattr("aqt_connector.log_in", lambda _: token)
    monkeypatch.setattr("aqt_connector.get_access_token", lambda _: token)


def lists_accessible_workspaces(cloud_provider_config: ArnicaConfig) -> set[str]:
    """Lists the workspaces accessible to the user.

    Args:
        cloud_provider_config (ArnicaConfig): The configuration for the cloud provider.

    Returns:
        set[str]: The set of accessible workspace IDs.
    """
    with AQTProvider() as provider:
        workspace_collection = provider.cloud(cloud_provider_config).fetch_workspaces()
        return {w.id for w in workspace_collection}


def lists_cloud_backends_in_workspace(cloud_provider_config: ArnicaConfig, workspace_id: str) -> set[str]:
    """Lists the cloud backends available in a specific workspace.

    Args:
        cloud_provider_config (ArnicaConfig): The configuration for the cloud provider.
        workspace_id (str): The ID of the workspace to list backends from.

    Returns:
        set[str]: The set of backend IDs available in the specified workspace.
    """
    with AQTProvider() as provider:
        workspace_collection = provider.cloud(cloud_provider_config).fetch_workspaces()
        workspace_provider = workspace_collection.get_by_id(workspace_id)
        if workspace_provider is None:
            raise ValueError(f"Workspace with ID '{workspace_id}' not found.")
        return {b.id for b in workspace_provider.list_backends()}


def acquires_backend_from_workspace(
    cloud_provider_config: ArnicaConfig, workspace_id: str, backend_id: str
) -> CloudResource:
    """Acquires a backend by exact identifier from a specific workspace.

    Args:
        cloud_provider_config (ArnicaConfig): The configuration for the cloud provider.
        workspace_id (str): The ID of the workspace to acquire the backend from.
        backend_id (str): The ID of the backend to acquire.

    Returns:
        CloudResource: The acquired backend, fully hydrated with details from the cloud provider
            and retaining its workspace context.
    """
    with AQTProvider() as provider:
        workspace_collection = provider.cloud(cloud_provider_config).fetch_workspaces()
        workspace_provider = workspace_collection.get_by_id(workspace_id)
        if workspace_provider is None:
            raise ValueError(f"Workspace with ID '{workspace_id}' not found.")
        return workspace_provider.get_backend(backend_id)


def submits_circuit(
    cloud_provider_config: ArnicaConfig, workspace_id: str, backend_id: str, circuit: Union[QuantumCircuit, list[QuantumCircuit]], shots: Optional[int] = None
) -> CloudJob:
    """Submits a job to a specific backend in a specific workspace.

    Args:
        cloud_provider_config (ArnicaConfig): The configuration for the cloud provider.
        workspace_id (str): The ID of the workspace to submit the job to.
        backend_id (str): The ID of the backend to submit the job to.
        circuit (Union[QuantumCircuit, list[QuantumCircuit]]): The quantum circuit(s) to submit as a job.
        shots (Optional[int]): The number of shots to use for the job execution. If None, the default from the backend will be used.

    Returns:
        CloudJob: The submitted job, with a stable identity and accessible for polling and result retrieval.
    """
    with AQTProvider() as provider:
        workspace_collection = provider.cloud(cloud_provider_config).fetch_workspaces()
        workspace_provider = workspace_collection.get_by_id(workspace_id)
        if workspace_provider is None:
            raise ValueError(f"Workspace with ID '{workspace_id}' not found.")
        backend = workspace_provider.get_backend(backend_id)
        return backend.run(circuit, shots=shots)

