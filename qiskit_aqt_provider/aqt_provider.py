from pathlib import Path
from types import TracebackType
from typing import Callable, Optional

import pydantic as pdt
from aqt_connector import ArnicaConfig

from qiskit_aqt_provider._cloud.provider import CloudProvider
from qiskit_aqt_provider.persistence import get_store_path

__all__ = ["AQTProvider"]


class AQTProviderConfig(pdt.BaseModel):
    store_path_fn: Callable[[Optional[Path]], Path] = get_store_path


class AQTProvider:
    """Provider for backends from Alpine Quantum Technologies (AQT)."""

    def __init__(self, *, _config: Optional[AQTProviderConfig] = None) -> None:
        """Initialize the AQT provider.

        The AQT cloud portal URL can be configured using the ``AQT_ARNICA_URL``
        environment variable.
        """
        self._config = _config or AQTProviderConfig()
        self.name = "aqt_provider"
        self._cloud: Optional[CloudProvider] = None

    @property
    def cloud(self) -> CloudProvider:
        """The provider's cloud provider instance."""
        if self._cloud is None:
            config = ArnicaConfig(self._config.store_path_fn(None))
            self._cloud = CloudProvider(config)
        return self._cloud

    def __enter__(self) -> "AQTProvider":
        """Enters the runtime context for this provider."""
        return self

    def __exit__(
        self,
        exc_type: Optional[type[BaseException]],
        exc: Optional[BaseException],
        tb: Optional[TracebackType],
    ) -> None:
        """Exit the context manager and clean up resources."""
        if self._cloud is not None:
            self._cloud.close()
            self._cloud = None
