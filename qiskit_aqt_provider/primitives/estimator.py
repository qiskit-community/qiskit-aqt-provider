from copy import copy
from typing import Any, Optional

from qiskit import generate_preset_pass_manager
from qiskit.primitives import BackendEstimatorV2, PubResult
from qiskit.primitives.backend_estimator_v2 import (
    EstimatorPub,
    _PreprocessedData,
)

from qiskit_aqt_provider.aqt_resource import AnyAQTResource


class AQTEstimator(BackendEstimatorV2):
    """:class:`BaseEstimatorV2 <qiskit.primitives.BaseEstimatorV2>` primitive for AQT backends.

    As circuit transpilation for AQT backends includes angle wrapping, the transpilation needs to be done after
    parameter binding. In order for the AQTEstimator to support parameterized circuits, it needs to transpile circuits
    when it is run.

    For use cases where full control over transpilation is required and no parameterized circuits are used, the
    transpilation by the estimator can be skipped with the :attr:`skip_transpilation` parameter and backend-compatible
    circuits provided to the estimator.

    Providing options to the :class:`AQTEstimator` on instantiation will affect all circuit evaluations.
    Setting :class:`options <qiskit_aqt_provider.aqt_options.AQTOptions>` on the backend has the same effect.
    Passing options in :meth:`AQTEstimator.run <qiskit.primitives.BaseSamplerV2.run>` restricts the effect to that
    evaluation.
    """

    _backend: AnyAQTResource

    def __init__(
        self,
        *,
        backend: AnyAQTResource,
        options: Optional[dict[str, Any]] = None,
        skip_transpilation: bool = False,
        optimization_level: int = 0,
    ) -> None:
        """Initialize an ``Estimator`` primitive using an AQT backend.

        Args:
            backend: AQT resource to evaluate circuits on.
            options: options passed to through to the underlying
              :class:`BackendEstimatorV2 <qiskit.primitives.BackendEstimatorV2>`.
            skip_transpilation: if :data:`True`, do not transpile circuits
              before passing them to the execution backend, defaults to :data:`False`.
            optimization_level: the optimization level for transpilation, defaults to 0.
        """
        self.skip_transpilation = skip_transpilation
        self.optimization_level = optimization_level
        # disable progress bar
        backend.options.with_progress_bar = False
        # Set default precision in options so the amount of shots is the max amount possible
        options_copy = copy(options) if options is not None else {}
        if "default_precision" not in options_copy:
            # precision = 1/sqrt(shots), so shots = 1/precision^2
            # 0.022365 ≈ 1/sqrt(2000), resulting in ~2000 shots per circuit
            options_copy["default_precision"] = 0.022365

        super().__init__(
            backend=backend,
            options=options_copy,
        )

    @property
    def backend(self) -> AnyAQTResource:
        """Return the Estimator's backend."""
        return self._backend

    def _run_pubs(self, pubs: list[EstimatorPub], shots: int) -> list[PubResult]:
        """Compute results for pubs that all require the same value of ``shots``.

        Overrides the parent :class:`BaseEstimatorV2 <qiskit.primitives.BaseEstimatorV2>` function
        :meth: `_run_pubs` to check if the maximum amount of shots the backend is capable of, is not exceeded.
        """
        max_shots = type(self._backend.options).model_fields["shots"].metadata[1].le
        if max_shots and shots > max_shots:
            raise ValueError(
                f"Number of shots {shots} exceeds the backend's limit of {max_shots}. "
                "Consider reducing the precision of the estimation.",
            )

        results: list[PubResult] = super()._run_pubs(pubs=pubs, shots=shots)
        return results

    def _preprocess_pub(self, pub: EstimatorPub) -> _PreprocessedData:
        """Converts a pub into a list of bound circuits necessary to estimate all its observables.

        Overrides the parent :class:`BaseEstimatorV2 <qiskit.primitives.BaseEstimatorV2>` function
        :meth: `_preprocess_pub` to transpile circuits for the backend, unless actively skipped.

        Args:
            pub: The pub to preprocess.

        Returns:
            The values ``(circuits, bc_param_ind, bc_obs)`` where ``circuits`` are the circuits to
            execute on the backend, ``bc_param_ind`` are indices of the pub's bindings array and
            ``bc_obs`` is the observables array, both broadcast to the shape of the pub.
        """
        data: _PreprocessedData = super()._preprocess_pub(pub)

        if self.skip_transpilation:
            return data

        pm = generate_preset_pass_manager(backend=self._backend, optimization_level=self.optimization_level)
        # don't use pass_manager.run(bound_circuits). It starts several processes and is slower
        final_circuits = [pm.run(qc) for qc in data.circuits]

        return _PreprocessedData(final_circuits, data.parameter_indices, data.observables)
