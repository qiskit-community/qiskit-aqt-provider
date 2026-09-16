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
from aqt_connector import ArnicaApp, ArnicaConfig

from qiskit_aqt_provider._cloud.provider import CloudProvider


def test_it_logs_in_with_provided_config(monkeypatch: pytest.MonkeyPatch) -> None:
    """The CloudProvider should log in using the provided configuration."""
    given_app: ArnicaApp | None = None

    def _log_in_handler(app: ArnicaApp) -> str:
        nonlocal given_app
        given_app = app
        return "arnica.token"

    monkeypatch.setattr("aqt_connector.log_in", _log_in_handler)
    config = ArnicaConfig()
    provider = CloudProvider(config)

    provider.log_in()

    assert given_app is not None
    assert given_app.config is config
