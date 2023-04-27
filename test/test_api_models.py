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

from qiskit_aqt_provider import api_models, api_models_generated


def test_workspaces_filter_by_workspace() -> None:
    """Test filtering the Workspaces model content by workspace ID."""
    workspaces = api_models.Workspaces(
        __root__=[
            api_models_generated.Workspace(id="w1", resources=[]),
            api_models_generated.Workspace(id="w2", resources=[]),
        ]
    )

    filtered = workspaces.filter(workspace_pattern="^w")
    assert {workspace.id for workspace in filtered.__root__} == {"w1", "w2"}

    filtered = workspaces.filter(workspace_pattern="w1")
    assert {workspace.id for workspace in filtered.__root__} == {"w1"}


def test_workspaces_filter_by_name() -> None:
    """Test filtering the Workspaces model content by backend ID."""
    workspaces = api_models.Workspaces(
        __root__=[
            api_models_generated.Workspace(
                id="w1",
                resources=[
                    api_models_generated.Resource(
                        id="r10", name="r10", type=api_models.ResourceType.device
                    ),
                    api_models_generated.Resource(
                        id="r20", name="r20", type=api_models.ResourceType.device
                    ),
                ],
            ),
            api_models_generated.Workspace(
                id="w2",
                resources=[
                    api_models_generated.Resource(
                        id="r11", name="r11", type=api_models.ResourceType.simulator
                    )
                ],
            ),
        ]
    )

    filtered = workspaces.filter(name_pattern="^r1")

    assert filtered == api_models.Workspaces(
        __root__=[
            api_models_generated.Workspace(
                id="w1",
                resources=[
                    api_models_generated.Resource(
                        id="r10", name="r10", type=api_models.ResourceType.device
                    ),
                ],
            ),
            api_models_generated.Workspace(
                id="w2",
                resources=[
                    api_models_generated.Resource(
                        id="r11", name="r11", type=api_models.ResourceType.simulator
                    )
                ],
            ),
        ]
    )


def test_workspaces_filter_by_backend_type() -> None:
    """Test filtering the Workspaces model content by backend type."""
    workspaces = api_models.Workspaces(
        __root__=[
            api_models_generated.Workspace(
                id="w1",
                resources=[
                    api_models_generated.Resource(
                        id="r1", name="r1", type=api_models.ResourceType.device
                    ),
                    api_models_generated.Resource(
                        id="r2", name="r2", type=api_models.ResourceType.simulator
                    ),
                ],
            )
        ]
    )

    filtered = workspaces.filter(backend_type=api_models.ResourceType.simulator)
    assert len(filtered.__root__) == 1
    assert filtered.__root__[0] == api_models_generated.Workspace(
        id="w1",
        resources=[
            api_models_generated.Resource(
                id="r2", name="r2", type=api_models.ResourceType.simulator
            )
        ],
    )
