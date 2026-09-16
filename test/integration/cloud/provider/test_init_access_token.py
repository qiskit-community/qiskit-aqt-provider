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

import pytest
from aqt_connector import ArnicaConfig

from qiskit_aqt_provider._cloud.provider import CloudProvider


def test_it_sets_authorization_header_on_init_when_access_token_exists(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """If a token is already available, CloudProvider should set the Authorization header at init."""
    monkeypatch.setattr("aqt_connector.get_access_token", lambda _app: "existing.token")

    provider = CloudProvider(ArnicaConfig())

    assert provider._http_client.headers.get("Authorization") == "Bearer existing.token"
    provider.close()


def test_it_does_not_set_authorization_header_on_init_when_access_token_missing(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """If no token is available, CloudProvider should not set the Authorization header at init."""
    monkeypatch.setattr("aqt_connector.get_access_token", lambda _app: None)

    provider = CloudProvider(ArnicaConfig())

    assert "Authorization" not in provider._http_client.headers
    provider.close()
