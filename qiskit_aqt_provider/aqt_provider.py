from types import TracebackType
from typing import Optional

from aqt_connector import ArnicaConfig

from qiskit_aqt_provider._cloud.provider import CloudProvider

__all__ = ["AQTProvider"]


class AQTProvider:
    """Provider for backends from Alpine Quantum Technologies (AQT)."""

    def __init__(self) -> None:
        """Initialize the AQT provider.

        The AQT cloud portal URL can be configured using the ``AQT_ARNICA_URL``
        environment variable.
        """
        self.name = "aqt_provider"
        self._cloud: Optional[CloudProvider] = None

    def cloud(self, config: Optional[ArnicaConfig] = None) -> CloudProvider:
        """The provider's cloud provider instance."""
        if self._cloud is None:
            config = config or ArnicaConfig()
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
