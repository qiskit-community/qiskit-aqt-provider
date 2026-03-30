from unittest import mock

from aqt_connector import ArnicaConfig

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
