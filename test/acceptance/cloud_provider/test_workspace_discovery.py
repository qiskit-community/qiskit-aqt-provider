from pathlib import Path

import pytest
from aqt_connector import ArnicaConfig

from test.acceptance import dsl
from test.acceptance.conftest import DummyArnicaServer


def test_lists_accessible_workspaces(
    monkeypatch: pytest.MonkeyPatch, dummy_server: DummyArnicaServer, tmp_path: Path
) -> None:
    """It should list workspaces accessible to the user.

    Given a cloud user with access to one or more workspaces
    When they list available workspaces
    Then they see each accessible workspace with a stable identifier
    """
    dsl.user.has_cloud_access(monkeypatch, "arnica_token")
    cloud_provider_config = ArnicaConfig(tmp_path)
    cloud_provider_config.arnica_url = dummy_server.base_url

    workspaces = dsl.user.lists_accessible_workspaces(cloud_provider_config)

    assert workspaces == {"w1", "w2", "w93"}


def test_lists_available_backends_in_workspace(
    monkeypatch: pytest.MonkeyPatch, dummy_server: DummyArnicaServer, tmp_path: Path
) -> None:
    """It should list backends available in a workspace.

    Given a workspace with assigned cloud resources
    When the user lists backends in that workspace
    Then they see the backends assigned to that workspace only
    """
    dsl.user.has_cloud_access(monkeypatch, "arnica_token")
    cloud_provider_config = ArnicaConfig(tmp_path)
    cloud_provider_config.arnica_url = dummy_server.base_url

    resources = dsl.user.lists_cloud_backends_in_workspace(cloud_provider_config, "w1")

    assert resources == {"r1", "r2"}


def test_same_underlying_resource_can_appear_in_multiple_workspaces(
    monkeypatch: pytest.MonkeyPatch, dummy_server: DummyArnicaServer, tmp_path: Path
) -> None:
    """The same underlying resource should be able to appear in multiple workspaces.

    Given a resource is accessible from two workspaces
    When the user lists backends in each workspace
    Then the shared resource appears in both workspace listings
    """
    dsl.user.has_cloud_access(monkeypatch, "arnica_token")
    cloud_provider_config = ArnicaConfig(tmp_path)
    cloud_provider_config.arnica_url = dummy_server.base_url

    workspace_ids = dsl.user.lists_accessible_workspaces(cloud_provider_config)
    workspace_backend_map = {
        workspace_id: dsl.user.lists_cloud_backends_in_workspace(cloud_provider_config, workspace_id)
        for workspace_id in workspace_ids
    }

    assert "r1" in workspace_backend_map["w1"]
    assert "r1" in workspace_backend_map["w2"]
