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

from pathlib import Path
from unittest import mock

import pytest
from aqt_connector import ArnicaApp, ArnicaConfig

from qiskit_aqt_provider._cloud.provider import CloudProvider


def test_close_closes_http_client() -> None:
    """CloudProvider.close should close its underlying HTTP client."""
    http_client = mock.Mock()

    provider = CloudProvider(
        ArnicaConfig(),
        http_client_factory=lambda _config: http_client,
    )

    provider.close()

    http_client.close.assert_called_once_with()


def test_it_creates_the_app_dir_before_persisting_tokens(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """CloudProvider creates the directory used by aqt-connector for token storage."""
    app_dir = tmp_path / ".aqt"
    provider = CloudProvider(ArnicaConfig(app_dir))

    def _log_in_and_save_token(app: ArnicaApp) -> str:
        app.auth_service.save_access_token("token")
        return "token"

    monkeypatch.setattr("aqt_connector.log_in", _log_in_and_save_token)

    provider.log_in()

    assert (app_dir / "access_token").read_text() == "token"
    provider.close()
