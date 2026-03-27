from typing import Optional

import pytest
from aqt_connector import ArnicaApp

from qiskit_aqt_provider._cloud.config import ArnicaConfig
from qiskit_aqt_provider._cloud.provider import CloudProvider


def test_it_logs_in_with_provided_config(monkeypatch: pytest.MonkeyPatch) -> None:
    """The CloudProvider should log in using the provided configuration."""
    given_app: Optional[ArnicaApp] = None

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
