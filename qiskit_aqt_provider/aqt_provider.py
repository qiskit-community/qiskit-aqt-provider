from types import TracebackType
from typing import Self

from aqt_connector import ArnicaConfig

from qiskit_aqt_provider._cloud.provider import CloudProvider
from qiskit_aqt_provider._direct.provider import DirectAccessProvider
from qiskit_aqt_provider._offline_sim.provider import OfflineSimulatorProvider

__all__ = ["AQTProvider"]


class AQTProvider:
    """Provider for backends from Alpine Quantum Technologies (AQT).

    Attibutes:
        name (str): The provider's name.
        offline (OfflineSimulatorProvider): The provider's offline simulator provider.
    """

    def __init__(self) -> None:
        """Initialize the AQT provider."""
        self.name = "aqt_provider"
        self._cloud: CloudProvider | None = None
        self._direct_access: DirectAccessProvider | None = None
        self.offline = OfflineSimulatorProvider()

    def cloud(self, config: ArnicaConfig | None = None) -> CloudProvider:
        """The provider's cloud provider instance."""
        if self._cloud is None:
            config = config or ArnicaConfig()
            self._cloud = CloudProvider(config)
        return self._cloud

    def direct_access(self) -> DirectAccessProvider:
        """The provider's direct access provider instance."""
        if self._direct_access is None:
            self._direct_access = DirectAccessProvider()
        return self._direct_access

    def __enter__(self) -> "Self":
        """Enters the runtime context for this provider."""
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        tb: TracebackType | None,
    ) -> None:
        """Exit the context manager and clean up resources."""
        if self._cloud is not None:
            self._cloud.close()
            self._cloud = None
        if self._direct_access is not None:
            self._direct_access.close()
            self._direct_access = None
