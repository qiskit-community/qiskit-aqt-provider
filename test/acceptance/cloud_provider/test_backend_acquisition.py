from pathlib import Path

import pytest
from aqt_connector import ArnicaConfig

from test.acceptance import dsl
from test.acceptance.conftest import DummyArnicaServer


def test_acquires_backend_by_exact_identifier_from_workspace(
    monkeypatch: pytest.MonkeyPatch, dummy_server: DummyArnicaServer, tmp_path: Path
) -> None:
    """A backend should be acquirable by exact identifier from a workspace.

    Given a workspace containing an assigned backend
    When the user acquires that backend by exact identifier
    Then they receive a fully hydrated backend bound to that workspace
    """
    dsl.user.has_cloud_access(monkeypatch, "arnica_token")
    cloud_provider_config = ArnicaConfig(tmp_path)
    cloud_provider_config.arnica_url = dummy_server.base_url

    acquired_backend = dsl.user.acquires_backend_from_workspace(
        cloud_provider_config, workspace_id="w1", backend_id="r1"
    )

    assert acquired_backend.id == "r1"
    assert acquired_backend.workspace_id == "w1"


def test_fails_to_acquire_unknown_backend_in_workspace(
    monkeypatch: pytest.MonkeyPatch, dummy_server: DummyArnicaServer, tmp_path: Path
) -> None:
    """A backend that is not in a workspace should not be acquirable from that workspace.

    Given a workspace that does not contain a backend
    When the user requests that backend from the workspace
    Then acquisition fails with a clear error
    """
    dsl.user.has_cloud_access(monkeypatch, "arnica_token")
    cloud_provider_config = ArnicaConfig(tmp_path)
    cloud_provider_config.arnica_url = dummy_server.base_url

    with dsl.expect.backend_not_found("w1", "r3"):
        dsl.user.acquires_backend_from_workspace(cloud_provider_config, workspace_id="w1", backend_id="r3")


def test_acquired_backend_preserves_workspace_context(
    monkeypatch: pytest.MonkeyPatch, dummy_server: DummyArnicaServer, tmp_path: Path
) -> None:
    """A backend acquired from a workspace should retain the identity of that workspace.

    Given a backend acquired from a workspace
    When the backend is inspected
    Then it retains the identity of the workspace it was acquired from
    """
    dsl.user.has_cloud_access(monkeypatch, "arnica_token")
    cloud_provider_config = ArnicaConfig(tmp_path)
    cloud_provider_config.arnica_url = dummy_server.base_url

    acquired_backend = dsl.user.acquires_backend_from_workspace(
        cloud_provider_config, workspace_id="w1", backend_id="r1"
    )

    assert acquired_backend.workspace_id == "w1"


def test_same_resource_can_be_acquired_from_multiple_workspaces(
    monkeypatch: pytest.MonkeyPatch, dummy_server: DummyArnicaServer, tmp_path: Path
) -> None:
    """The same underlying resource should be acquirable from multiple workspaces.

    Given two workspaces that both expose the same underlying resource
    When the user acquires that resource from each workspace
    Then each acquired backend remains bound to the workspace it came from
    """
    dsl.user.has_cloud_access(monkeypatch, "arnica_token")
    cloud_provider_config = ArnicaConfig(tmp_path)
    cloud_provider_config.arnica_url = dummy_server.base_url

    acquired_backend_1 = dsl.user.acquires_backend_from_workspace(
        cloud_provider_config, workspace_id="w1", backend_id="r1"
    )
    acquired_backend_2 = dsl.user.acquires_backend_from_workspace(
        cloud_provider_config, workspace_id="w2", backend_id="r1"
    )

    assert acquired_backend_1.id == acquired_backend_2.id
    assert acquired_backend_1.workspace_id == "w1"
    assert acquired_backend_2.workspace_id == "w2"
