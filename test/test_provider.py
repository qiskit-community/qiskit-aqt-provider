# This code is part of Qiskit.
#
# (C) Copyright IBM 2019, Alpine Quantum Technologies GmbH 2023.
#
# This code is licensed under the Apache License, Version 2.0. You may
# obtain a copy of this license in the LICENSE.txt file in the root directory
# of this source tree or at http://www.apache.org/licenses/LICENSE-2.0.
#
# Any modifications or derivative works of this code must retain this
# copyright notice, and modified files need to carry a notice indicating
# that they have been altered from the originals.

import os
import uuid
from pathlib import Path
from unittest import mock
from urllib.parse import urlparse

import pytest

from qiskit_aqt_provider.aqt_provider import AQTProvider


def test_default_portal_url() -> None:
    """Check that by default, the portal url is that of the class variable."""
    aqt = AQTProvider("my-token")

    result = urlparse(aqt.portal_url)
    expected = urlparse(AQTProvider.DEFAULT_PORTAL_URL)

    assert result.scheme == expected.scheme
    assert result.netloc == expected.netloc


def test_portal_url_envvar(monkeypatch: pytest.MonkeyPatch) -> None:
    """Check that one can set the portal url via the environment variable."""
    env_url = "https://new-portal.aqt.eu"
    assert env_url != AQTProvider.DEFAULT_PORTAL_URL
    monkeypatch.setenv("AQT_PORTAL_URL", env_url)

    aqt = AQTProvider("my-token")

    result = urlparse(aqt.portal_url)
    expected = urlparse(env_url)

    assert result.scheme == expected.scheme
    assert result.netloc == expected.netloc


def test_access_token_argument() -> None:
    """Check that one can set the access token via the init argument."""
    token = str(uuid.uuid4())
    aqt = AQTProvider(token)
    assert aqt.access_token == token


def test_access_token_envvar(monkeypatch: pytest.MonkeyPatch) -> None:
    """Check that one can set the access token via the environment variable."""
    token = str(uuid.uuid4())
    monkeypatch.setenv("AQT_TOKEN", token)

    aqt = AQTProvider()
    assert aqt.access_token == token


def test_access_token_argument_precendence_over_envvar(monkeypatch: pytest.MonkeyPatch) -> None:
    """Check that the argument has precedence over the environment variable for setting
    the access token."""
    arg_token = str(uuid.uuid4())
    env_token = str(uuid.uuid4())
    assert arg_token != env_token

    monkeypatch.setenv("AQT_TOKEN", env_token)

    aqt = AQTProvider(arg_token)
    assert aqt.access_token == arg_token


def test_autoload_env(tmp_path: Path) -> None:
    """Check that the environment variables are loaded from disk by default.

    We don't check the functionality of the python-dotenv library, only that the
    loading call is active by default in `AQTProvider.__init__`.
    """
    env_token = str(uuid.uuid4())
    dotenv_path = tmp_path / "env"
    dotenv_path.write_text(f'AQT_TOKEN = "{env_token}"')

    mocked_env = os.environ.copy()
    with mock.patch.object(os, "environ", mocked_env):
        aqt = AQTProvider(dotenv_path=dotenv_path)
        assert aqt.access_token == env_token


def test_autoload_env_deactivated(tmp_path: Path) -> None:
    """Check that auto-loading the environment can be deactivated."""
    env_token = str(uuid.uuid4())
    dotenv_path = tmp_path / "env"
    dotenv_path.write_text(f'AQT_TOKEN = "{env_token}"')

    mocked_env = os.environ.copy()
    with mock.patch.object(os, "environ", mocked_env):
        with pytest.raises(ValueError) as excinfo:
            AQTProvider(load_dotenv=False)

    assert "No access token provided" in str(excinfo)


def test_access_token_missing() -> None:
    """Check that it is an error to not set an access token."""
    with pytest.raises(ValueError) as excinfo:
        AQTProvider()

    assert "No access token provided" in str(excinfo)
