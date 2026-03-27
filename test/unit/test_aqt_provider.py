from unittest import mock

from qiskit_aqt_provider.aqt_provider import AQTProvider


def test_cloud_is_not_instantiate_on_provider_init() -> None:
    """The AQT provider should not instantiate its cloud provider on initialization."""
    p = AQTProvider()

    assert p._cloud is None


def test_cloud_is_cached() -> None:
    """The AQT provider should cache the cloud provider instance it creates."""
    p = AQTProvider()
    first = p.cloud()
    second = p.cloud()

    assert first is second


def test_exit_closes_cloud_provider_and_clears_cached_instance() -> None:
    """Exiting the provider context should close and clear the cached cloud provider."""
    provider = AQTProvider()
    cloud_provider = mock.Mock()
    provider._cloud = cloud_provider

    provider.__exit__(None, None, None)

    cloud_provider.close.assert_called_once_with()
    assert provider._cloud is None


def test_exit_without_cloud_is_noop() -> None:
    """Exiting context without an instantiated cloud provider should be a no-op."""
    provider = AQTProvider()

    provider.__exit__(None, None, None)

    assert provider._cloud is None
