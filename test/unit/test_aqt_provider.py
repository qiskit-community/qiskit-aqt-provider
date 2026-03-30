from pathlib import Path

from qiskit_aqt_provider.aqt_provider import AQTProvider, AQTProviderConfig


def test_cloud_is_not_instantiate_on_provider_init() -> None:
    """The AQT provider should not instantiate its cloud provider on initialization."""
    p = AQTProvider()

    assert p._cloud is None


def test_cloud_is_cached() -> None:
    """The AQT provider should cache the cloud provider instance it creates."""
    p = AQTProvider()
    first = p.cloud
    second = p.cloud

    assert first is second


def test_cloud_is_created_with_configured_store_path(tmp_path: Path) -> None:
    """The AQT provider should create its cloud provider with a config that uses the configured store path."""
    store_path = tmp_path / "store"
    config = AQTProviderConfig(store_path_fn=lambda _: store_path)
    p = AQTProvider(_config=config)

    assert p.cloud._arnica.config._app_dir == store_path
