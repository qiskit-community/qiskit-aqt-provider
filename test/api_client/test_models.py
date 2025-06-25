# This code is part of Qiskit.
#
# (C) Copyright Alpine Quantum Technologies GmbH 2023.
#
# This code is licensed under the Apache License, Version 2.0. You may
# obtain a copy of this license in the LICENSE.txt file in the root directory
# of this source tree or at http://www.apache.org/licenses/LICENSE-2.0.
#
# Any modifications or derivative works of this code must retain this
# copyright notice, and modified files need to carry a notice indicating
# that they have been altered from the originals.

import pytest

from qiskit_aqt_provider.api_client import models as api_models


def test_workspaces_container_empty() -> None:
    """Test the empty edge case of the Workspaces container."""
    empty = api_models.Workspaces(root=[])
    assert len(empty) == 0

    with pytest.raises(StopIteration):
        next(iter(empty))

    assert api_models.Workspace(workspace_id="w1", resources=[]) not in empty


def test_workspaces_contains() -> None:
    """Test the Workspaces.__contains__ implementation."""
    workspaces = api_models.Workspaces(
        root=[
            api_models.Workspace(workspace_id="w1", resources=[]),
        ]
    )

    assert api_models.Workspace(workspace_id="w1", resources=[]) in workspaces
    assert api_models.Workspace(workspace_id="w2", resources=[]) not in workspaces


def test_workspaces_filter_by_workspace() -> None:
    """Test filtering the Workspaces model content by workspace ID."""
    workspaces = api_models.Workspaces(
        root=[
            api_models.Workspace(workspace_id="w1", resources=[]),
            api_models.Workspace(workspace_id="w2", resources=[]),
        ]
    )

    filtered = workspaces.filter(workspace_pattern="^w")
    assert {workspace.workspace_id for workspace in filtered} == {"w1", "w2"}

    filtered = workspaces.filter(workspace_pattern="w1")
    assert {workspace.workspace_id for workspace in filtered} == {"w1"}


def test_workspaces_filter_by_name() -> None:
    """Test filtering the Workspaces model content by backend ID."""
    workspaces = api_models.Workspaces(
        root=[
            api_models.Workspace(
                workspace_id="w1",
                resources=[
                    api_models.Resource(
                        workspace_id="w1",
                        resource_id="r10",
                        resource_name="r10",
                        resource_type="device",
                        available_qubits=20,
                    ),
                    api_models.Resource(
                        workspace_id="w1",
                        resource_id="r20",
                        resource_name="r20",
                        resource_type="device",
                        available_qubits=20,
                    ),
                ],
            ),
            api_models.Workspace(
                workspace_id="w2",
                resources=[
                    api_models.Resource(
                        workspace_id="w2",
                        resource_id="r11",
                        resource_name="r11",
                        resource_type="simulator",
                        available_qubits=20,
                    )
                ],
            ),
        ]
    )

    filtered = workspaces.filter(name_pattern="^r1")

    assert filtered == api_models.Workspaces(
        root=[
            api_models.Workspace(
                workspace_id="w1",
                resources=[
                    api_models.Resource(
                        workspace_id="w1",
                        resource_id="r10",
                        resource_name="r10",
                        resource_type="device",
                        available_qubits=20,
                    ),
                ],
            ),
            api_models.Workspace(
                workspace_id="w2",
                resources=[
                    api_models.Resource(
                        workspace_id="w2",
                        resource_id="r11",
                        resource_name="r11",
                        resource_type="simulator",
                        available_qubits=20,
                    )
                ],
            ),
        ]
    )


def test_workspaces_filter_by_backend_type() -> None:
    """Test filtering the Workspaces model content by backend type."""
    workspaces = api_models.Workspaces(
        root=[
            api_models.Workspace(
                workspace_id="w1",
                resources=[
                    api_models.Resource(
                        workspace_id="w1",
                        resource_id="r1",
                        resource_name="r1",
                        resource_type="device",
                        available_qubits=20,
                    ),
                    api_models.Resource(
                        workspace_id="w1",
                        resource_id="r2",
                        resource_name="r2",
                        resource_type="simulator",
                        available_qubits=20,
                    ),
                ],
            )
        ]
    )

    filtered = workspaces.filter(backend_type="simulator")
    assert len(filtered) == 1
    assert next(iter(filtered)) == api_models.Workspace(
        workspace_id="w1",
        resources=[
            api_models.Resource(
                workspace_id="w1",
                resource_id="r2",
                resource_name="r2",
                resource_type="simulator",
                available_qubits=20,
            )
        ],
    )
