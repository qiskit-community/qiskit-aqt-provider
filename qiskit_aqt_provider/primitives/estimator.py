from __future__ import annotations

from collections.abc import Callable, Iterable
from typing import Any

from qiskit.primitives import (
    BackendEstimatorV2,
    BaseEstimatorV2,
    BasePrimitiveJob,
    PrimitiveResult,
    PubResult,
)
from qiskit.primitives.containers.estimator_pub import EstimatorPubLike
from qiskit.providers import BackendV2, Options

from qiskit_aqt_provider.aqt_provider import AnyAQTResource
from qiskit_aqt_provider.primitives._transpiling_backend import TranspilingBackend

BackendFactory = Callable[[AnyAQTResource], BackendV2]
EstimatorFactory = Callable[[BackendV2, dict[str, Any] | None], BaseEstimatorV2]


class AQTEstimator(BaseEstimatorV2):
    """:class:`BaseEstimatorV2 <qiskit.primitives.BaseEstimatorV2>` primitive for AQT backends.

    As circuit transpilation for AQT backends includes angle wrapping, the transpilation needs to be done after
    parameter binding. In order for the AQTEstimator to support parameterized circuits, it needs to transpile circuits
    when it is run.

    Providing options to the :class:`AQTEstimator` on instantiation will affect all circuit evaluations.
    Setting :class:`options <qiskit_aqt_provider.aqt_options.AQTOptions>` on the backend has the same effect.
    Passing options in :meth:`AQTEstimator.run <qiskit.primitives.BaseEstimatorV2.run>` restricts the effect to that
    evaluation.
    """

    def __init__(
        self,
        *,
        backend: AnyAQTResource,
        options: dict[str, Any] | None = None,
    ) -> None:
        self.backend = backend
        self._options = options or Options()

        self.backend_factory: BackendFactory = TranspilingBackend
        self.estimator_factory: EstimatorFactory = lambda b, o: BackendEstimatorV2(backend=b, options=o)

    def run(
        self, pubs: Iterable[EstimatorPubLike], *, precision: float | None = None
    ) -> BasePrimitiveJob[PrimitiveResult[PubResult]]:
        """Run the given estimator PUBs on the AQT backend.

        Args:
            pubs (Iterable[EstimatorPubLike]): An iterable of estimator PUBs, which may include parameterized
                circuits and associated parameter values.
            precision (float | None, optional): The precision to use for the estimation. Defaults to None.

        Returns:
            BasePrimitiveJob[PrimitiveResult[PubResult]]: A job representing the execution of the estimator PUBs.
        """
        wrapped_backend = self.backend_factory(self.backend)
        delegate = self.estimator_factory(wrapped_backend, self._options)
        return delegate.run(pubs, precision=precision)
