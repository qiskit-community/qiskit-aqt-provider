from qiskit.provider.providerutils import filter_backends
from qiskit.providers import BaseProvider

from qiskit_aqt.aqt_backend import AQTBackend


class AQTProvider(BaseProvider):
    """Provider for the Hadamard backend"""

    def __init__(self, access_token):
        super().__init__()

        self.access_token = access_token
        # Populate the list of Hadamard backends
        self._backends = [AQTBackend(provider=self)]

    def backends(self, name=None, filters=None, **kwargs):
        # pylint: disable=arguments-differ
        backends = self._backends
        if name:
            backends = [
                backend for backend in backends if backend.name() == name]

        return filter_backends(backends, filters=filters, **kwargs)
