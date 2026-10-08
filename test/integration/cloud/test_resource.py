# This code is part of Qiskit.
#
# (C) Copyright Alpine Quantum Technologies GmbH 2023
#
# This code is licensed under the Apache License, Version 2.0. You may
# obtain a copy of this license in the LICENSE.txt file in the root directory
# of this source tree or at [http://www.apache.org/licenses/LICENSE-2.0](http://www.apache.org/licenses/LICENSE-2.0).
#
# Any modifications or derivative works of this code must retain this
# copyright notice, and modified files need to carry a notice indicating
# that they have been altered from the originals.

from datetime import datetime

from aqt_connector import ArnicaApp
from aqt_connector.models.arnica.resources import ResourceStatus, ResourceType
from aqt_connector.models.arnica.response_bodies.resources import ResourceDetails
from httpx import Client, MockTransport, Response

from qiskit_aqt_provider._cloud.resource import CloudResource


def test_id_property_returns_resource_id() -> None:
    """The workspace provider's ID property should return the workspace's identifier."""
    resource = CloudResource(
        ArnicaApp(),
        Client(transport=MockTransport(lambda _: Response(404))),
        "workspace_id",
        ResourceDetails(
            id="w1",
            name="W1",
            type=ResourceType.DEVICE,
            status=ResourceStatus.ONLINE,
            available_qubits=20,
            status_updated_at=datetime(2026, 3, 27, 0, 0, 0),
        ),
    )

    assert resource.id == "w1"
