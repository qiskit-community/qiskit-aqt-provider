from collections.abc import Callable, Sequence

from qiskit import transpile
from qiskit.circuit import QuantumCircuit
from qiskit.providers import BackendV2, JobV1, Options
from qiskit.transpiler import Target
from typing_extensions import Unpack

from qiskit_aqt_provider.aqt_provider import AnyAQTResource
from qiskit_aqt_provider.options import ResourceRunOptions


def _transpile(
    circuit: QuantumCircuit | Sequence[QuantumCircuit], backend: BackendV2
) -> QuantumCircuit | Sequence[QuantumCircuit]:
    """Transpile the given circuit(s) for the given backend, using no optimization."""
    return transpile(circuit, backend=backend, optimization_level=0)


class TranspilingBackend(BackendV2):
    """A backend that transpiles circuits for the target resource before running them."""

    def __init__(
        self,
        backend: AnyAQTResource,
        *,
        transpile_fn: Callable[
            [QuantumCircuit | Sequence[QuantumCircuit], BackendV2],
            QuantumCircuit | Sequence[QuantumCircuit],
        ] = _transpile,
    ) -> None:
        """Initialize the backend."""
        self._backend = backend
        self._transpile = transpile_fn
        super().__init__(name=backend.name)
        self._options = type(backend)._default_options()  # overwrite with real defaults

    @property
    def id(self) -> str:
        """The resource's identifier."""
        return self._backend.id

    @property
    def target(self) -> Target:
        """The resource's target."""
        return self._backend.target

    @property
    def max_circuits(self) -> int:
        """Maximum number of circuits per batch."""
        return self._backend.max_circuits

    @classmethod
    def _default_options(cls) -> Options:
        """Get the default options.

        Returns:
            Options: The default options for this resource.
        """
        return Options()

    def run(
        self,
        circuit: QuantumCircuit | Sequence[QuantumCircuit],
        **kwargs: Unpack[ResourceRunOptions],
    ) -> JobV1:
        """Run the given circuit(s) on the backend, after transpiling them for the backend's target."""
        transpiled = self._transpile(circuit, self._backend)
        return self._backend.run(transpiled, **kwargs)
